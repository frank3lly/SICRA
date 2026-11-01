# Guia de Integracion de Hardware y Firmware ESP32 para Contenedores SICRA

Esta guia esta dirigida al ingeniero electromecanico o encargado del desarrollo del firmware en los microcontroladores ESP32 de los contenedores inteligentes de aceite vegetal usado. El proposito de este documento es explicar de forma clara, practica y sin rodeos como debe comunicarse el microcontrolador con el servidor de SICRA, que datos debe enviar, como manejar los cortes de red y por que ciertas decisiones de diseño se tomaron de esta manera.

---

## 1. Filosofia del Dispositivo: Un Transductor Robusto, no un Ordenador Complejo

En sistemas de telemetria industrial para entornos hostiles (como la cocina de un restaurante o freiduria, con altas temperaturas, grasa en suspension, humedad e interferencias electricas), el microcontrolador debe mantenerse lo mas simple, confiable y autonomo posible.

La regla de oro para el ESP32 es: **mide magnitudes fisicas directas (voltios, milivoltios y kilogramos brutos) y transmitelas tal cual**. El microcontrolador no debe tomar decisiones de negocio, no debe calcular rutas, no debe adivinar si el contenedor esta lleno o vacio, y no debe convertir unidades. Toda la logica de inteligencia, calibraciones y alertas la ejecuta el servidor.

---

## 2. Por que la Tara y los Litros se Calculan en el Servidor y NO en el ESP32

Una duda muy comun al diseñar el firmware de una balanza inteligente es: *¿por que no guardar el peso del tanque vacio (la tara) en la memoria del ESP32 y enviar directamente los litros de aceite?*

Existen tres razones fundamentales de ingenieria para no hacerlo en el microcontrolador:

### Analogia del Taller Mecanico y el Reemplazo de Piezas
Imagina que en un restaurante el tanque plastico de 50 litros se agrieta o se daña con el calor. El equipo de mantenimiento va al local y reemplaza el tanque viejo por otro que tenian en almacen, o incluso deciden cambiarlo temporalmente por un tanque de 20 litros o colocarle una abrazadera metalica de refuerzo. Cada uno de esos elementos fisicos cambia el peso vacio de la estructura (la tara).

Si la tara estuviese grabada en el codigo del ESP32, tendrias que mandar a un programador con una computadora portatil, desarmar la caja estanca sellada con silicon o prensaestopas, conectar un cable USB y reprogramar el firmware solo para actualizar ese valor. 

Al manejar la tara en el servidor, el personal de campo simplemente registra en la aplicacion web el nuevo peso del tambor instalado. El ESP32 sigue midiendo y enviando kilogramos brutos sin necesidad de tocar una sola linea de codigo ni abrir la caja electronica.

### La Densidad del Aceite Usado no es Constante
El agua pesa exactamente un kilogramo por litro a temperatura estandar. El aceite de cocina usado no. Su densidad ronda los 0.92 kilogramos por litro, pero varia ligeramente dependiendo de la mezcla de aceites (soya, maiz, palma) y de la temperatura ambiente de la cocina (un aceite a 35 grados Celsius ocupa un volumen diferente al mismo aceite a 20 grados). El servidor cuenta con parametros de densidad ajustables por tipo de negocio y modelo matematico, liberando al microcontrolador de realizar operaciones de punto flotante que consumen ciclos de reloj y bateria.

### Integridad y Repetibilidad Metrologica
Si el microcontrolador realizara restas y divisiones internamente y se descalibrara en campo, los datos historicos enviados quedarian falseados para siempre. Al recibir la masa bruta directa, si en algun momento se descubre que la base mecanica tenia una deformacion constante de 300 gramos, el servidor puede recalibrar los datos historicos retroactivamente en la base de datos sin perder informacion.

---

## 3. Que Informacion Debe Enviar el Contenedor

Para cada medicion, el servidor espera exactamente los siguientes datos:

1. **Token del Dispositivo (`device_token`):** Es una cadena de texto unica asignada al contenedor (por ejemplo, `sicra_live_tok_spm_biz_001_8b3a7dc92e104f5a`). Funciona como la matricula o cedula de identidad electronica del recipiente. Si el token no coincide con ningun contenedor activo en la base de datos, el servidor rechazara la transmision.
2. **Estampa de Tiempo (`timestamp`):** La fecha y hora exacta en formato estandar internacional UTC ISO-8601 (por ejemplo: `2026-11-01T14:30:00Z`). Es indispensable para saber en que momento exacto se registro el peso, especialmente cuando hubo cortes de red.
3. **Peso Bruto en Kilogramos (`raw_weight_kg`):** El valor de peso medido por la celda de carga a traves del amplificador HX711 (o similar), expresado en kilogramos con precision de uno o dos decimales (por ejemplo, `42.50`). Este peso incluye la estructura del contenedor mas el aceite que tenga adentro.
4. **Voltaje de Bateria en Milivoltios (`battery_mv`):** El voltaje de la bateria de alimentacion medido mediante un divisor de tension resistivo conectado a un canal analogico (ADC) del ESP32. Por ejemplo, `4150` para una bateria de litio totalmente cargada o `3500` cuando se encuentra en nivel critico. El servidor se encarga de convertir este valor en porcentaje de salud de bateria.

---

## 4. Como Manejar los Cortes de Red Wi-Fi (Soporte de Lotes Desconectados)

En las cocinas de restaurantes, el enlace Wi-Fi suele ser inestable debido a paredes gruesas, interferencias electromagneticas de motores de refrigeracion o cortes temporales de suministro electrico.

### La Analogia de la Libreta del Repartidor
Si un repartidor va a entregar paquetes en una zona sin cobertura celular, no se detiene ni tira las notas de entrega a la basura; las anota en su libreta con la hora en que llego y, al volver a tener señal, entrega todas las notas juntas en la oficina central.

El firmware del ESP32 debe operar con esa misma logica:
* Cada vez que el microcontrolador despierte y tome una lectura de peso, intentara conectarse a la red Wi-Fi y transmitir.
* Si no hay conexion disponible, el ESP32 **debe guardar la lectura en su memoria flash interna** (utilizando el sistema de archivos SPIFFS o LittleFS de la libreria de Arduino/ESP-IDF), registrando la fecha/hora y el peso en un archivo o cola local.
* Cuando la conexion se restablezca (ya sea 2 horas o 3 dias despues), el ESP32 leera todas las lecturas acumuladas en la memoria flash y las enviara en una sola peticion HTTP dentro de una lista o arreglo JSON.
* El servidor de SICRA esta diseñado especificamente para recibir lotes de hasta mil lecturas consecutivas. El servidor las ordenara por fecha, las insertara cronologicamente en la base de datos y descartara automaticamente las que ya hubiese recibido previamente, sin que se generen errores de duplicidad.

---

## 5. Protocolo de Comunicacion y Formato de los Mensajes

La comunicacion se realiza mediante el protocolo estandar **HTTP POST** (o HTTPS).

* **Direccion del Servicio (URL):**  
  `https://tu-servidor-sicra.onrender.com/api/v1/telemetry/ingest`  
  *(o la direccion IP local si estas realizando pruebas en banco de trabajo)*
* **Cabeceras HTTP Requeridas (Headers):**  
  * `Content-Type: application/json`
  * `X-Device-Token: tu_token_aqui` *(opcionalmente se puede colocar dentro del cuerpo del mensaje)*

### Formato JSON para Envio Normal en Tiempo Real (Una Lectura)
Cuando el Wi-Fi funciona correctamente y el sensor envia su reporte periodico regular:

```json
{
  "readings": [
    {
      "timestamp": "2026-11-01T14:30:00Z",
      "raw_weight_kg": 25.80,
      "battery_mv": 3950,
      "is_synthetic": false
    }
  ]
}
```

### Formato JSON para Envio en Lote Acumulado (Tras Corte de Wi-Fi)
Cuando el dispositivo estuvo desconectado y acumulo varias lecturas en su memoria flash:

```json
{
  "readings": [
    {
      "timestamp": "2026-11-01T08:00:00Z",
      "raw_weight_kg": 15.20,
      "battery_mv": 4020,
      "is_synthetic": false
    },
    {
      "timestamp": "2026-11-01T10:00:00Z",
      "raw_weight_kg": 18.40,
      "battery_mv": 4010,
      "is_synthetic": false
    },
    {
      "timestamp": "2026-11-01T12:00:00Z",
      "raw_weight_kg": 22.10,
      "battery_mv": 3990,
      "is_synthetic": false
    }
  ]
}
```

### Que Responde el Servidor
Si la transmision es correcta, el servidor devolvera un codigo **HTTP 200 OK** con una respuesta como esta:

```json
{
  "status": "success",
  "container_id": "e3a89100-c9fa-4155-9a88-db1a4d081190",
  "accepted_count": 3,
  "duplicate_count": 0,
  "current_volume_liters": 16.96,
  "current_fill_percentage": 33.91,
  "drain_events_detected": 0,
  "alerts_triggered": 0,
  "alerts_resolved": 0
}
```

Si el servidor responde:
* **HTTP 401 Unauthorized:** El token enviado es incorrecto o el contenedor fue dado de baja administrativamente. Revisa que el token grabado en el ESP32 coincida con el asignado en la base de datos.
* **HTTP 400 Bad Request:** El texto JSON esta mal formado (por ejemplo, falta una llave de cierre, hay una coma sobrante o los nombres de los campos estan mal escritos).

---

## 6. Buenas Practicas de Ingenieria para el Firmware del ESP32

Para asegurar una instalacion industrial duradera y libre de fallos en campo, se recomienda incorporar las siguientes pautas en el codigo:

### 1. Filtrado de Ruido y Vibraciones en la Celda de Carga
En las cocinas hay constantes pisadas, cierres de puertas y caida de utensilios que provocan vibraciones mecanicas instantaneas en la celda de carga. No tomes una sola muestra instantanea del convertidor analogico a digital (HX711). Lo recomendable es tomar entre 10 y 16 muestras consecutivas en un intervalo de 2 segundos, descartar el valor maximo y el valor minimo (filtro de mediana o promedio truncado) y calcular la media del resto.

### 2. Sincronizacion de Reloj (NTP o RTC Externo)
Dado que el servidor exige una estampa de tiempo valida para cada medicion, el ESP32 debe sincronizar su reloj interno mediante el protocolo NTP (`pool.ntp.org`) cada vez que disponga de conexion a internet. Si el dispositivo va a operar en sitios donde los cortes de internet pueden durar semanas, es aconsejable incluir un chip RTC externo de bajo consumo con bateria de respaldo (como el DS3231) conectado por bus I2C.

### 3. Gestion de Energia y Modo de Sueño Profundo (Deep Sleep)
El aceite vegetal usado no se genera de forma instantanea en cuestion de segundos, sino a lo largo de turnos de coccion de varias horas. No tiene sentido mantener el modem Wi-Fi del ESP32 encendido continuamente consumiendo 120 mA.  
El ciclo de trabajo recomendado es:
1. Despertar del sueño profundo cada 1 hora (o cada 30 minutos durante las horas pico de operacion del negocio).
2. Alimentar el amplificador HX711 a traves de un transistor MOSFET o pin GPIO de habilitacion.
3. Esperar 100 milisegundos a que se estabilice el sensor y promediar las lecturas de peso.
4. Leer el voltaje de la bateria.
5. Encender el radio Wi-Fi e intentar transmitir al servidor.
6. Si transmite exitosamente, limpiar el buffer de lecturas acumuladas en la memoria flash. Si falla, agregar la medicion al archivo local de respaldo.
7. Desconectar Wi-Fi, desenergizar sensores y entrar inmediatamente en Deep Sleep (consumo menor a 15 microamperios). Con esta rutina, una bateria de litio 18650 estandar puede durar entre 6 meses y 1 año sin requerir recarga.
