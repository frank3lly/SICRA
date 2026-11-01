import React, { useState } from 'react';
import Header from './components/layout/Header';
import {
  Button,
  Card,
  StatWidget,
  ProgressBar,
  Chip,
  SegmentedControl,
  DropIcon,
  CloudIcon,
  TruckIcon,
  BellIcon,
  SparkIcon,
  PlusIcon,
  ShieldIcon,
  LeafIcon,
  ClockIcon,
  BatteryIcon,
  RouteIcon,
  DownloadIcon,
  ExpandIcon
} from './components/common';

export function App() {
  const [role, setRole] = useState('admin');
  const [metricMode, setMetricMode] = useState('l');

  return (
    <div className="app">
      <Header role={role} setRole={setRole} />

      <main>
        {role === 'admin' && (
          <section id="admin">
            <div className="row sp" style={{ alignItems: 'flex-end' }}>
              <div>
                <h1>Panorama de la flota</h1>
              </div>
              <div className="row">
                <Button icon={<SparkIcon />}>
                  <span>Ejecutar proyección</span>
                </Button>
                <Button variant="p" icon={<PlusIcon />}>
                  Nuevo comercio
                </Button>
              </div>
            </div>

            <div className="grid g4" style={{ margin: '32px 0 16px' }}>
              <StatWidget
                icon={<DropIcon />}
                label="Aceite desviado"
                value="14.250 L"
              />
              <StatWidget
                icon={<CloudIcon />}
                label="CO₂ evitado"
                value="40.612 kg"
              />
              <StatWidget
                icon={<TruckIcon />}
                label="Recolecciones"
                value="312"
              />
              <StatWidget
                icon={<BellIcon />}
                label="Alertas activas"
                value="3"
              />
            </div>

            <div className="grid g2" style={{ marginTop: '16px' }}>
              <Card>
                <div className="row sp" style={{ marginBottom: '14px' }}>
                  <h2>Contenedores en Monitoreo</h2>
                  <span className="sm mut">5 activos</span>
                </div>
                <div className="scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Comercio</th>
                        <th>Llenado</th>
                        <th>Batería</th>
                        <th>Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Pica Pollo Expreso</td>
                        <td>
                          <div className="row">
                            <ProgressBar value={83} />
                            <span>83%</span>
                          </div>
                        </td>
                        <td>69%</td>
                        <td><Chip variant="w">Casi lleno</Chip></td>
                      </tr>
                      <tr>
                        <td>Frituras Doña Ana</td>
                        <td>
                          <div className="row">
                            <ProgressBar value={96} />
                            <span>96%</span>
                          </div>
                        </td>
                        <td>54%</td>
                        <td><Chip variant="c">Crítico</Chip></td>
                      </tr>
                      <tr>
                        <td>Cafetería Central</td>
                        <td>
                          <div className="row">
                            <ProgressBar value={41} />
                            <span>41%</span>
                          </div>
                        </td>
                        <td>88%</td>
                        <td><Chip>Normal</Chip></td>
                      </tr>
                      <tr>
                        <td>Comedor Los Pinos</td>
                        <td>
                          <div className="row">
                            <ProgressBar value={22} />
                            <span>22%</span>
                          </div>
                        </td>
                        <td>91%</td>
                        <td><Chip>Normal</Chip></td>
                      </tr>
                      <tr>
                        <td>Restaurante El Muelle</td>
                        <td>
                          <div className="row">
                            <ProgressBar value={80} />
                            <span>80%</span>
                          </div>
                        </td>
                        <td>18%</td>
                        <td><Chip variant="w">Batería baja</Chip></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </Card>

              <Card>
                <h2>Cumplimiento Ambiental</h2>
                <div style={{ margin: '10px 0 18px' }}>
                  <Chip>Ley 225-20</Chip>
                </div>
                <div className="note">
                  <LeafIcon />
                  <span>14.250.000 L de agua preservados por el aceite que no llegó al drenaje.</span>
                </div>
                <div style={{ marginTop: '18px' }}>
                  <Button variant="n" icon={<ShieldIcon />}>
                    Descargar reporte
                  </Button>
                </div>
              </Card>
            </div>
          </section>
        )}

        {role === 'col' && (
          <section id="col">
            <div className="row sp" style={{ alignItems: 'flex-end' }}>
              <div>
                <h1>Ruta de hoy</h1>
              </div>
              <div className="row">
                <Button icon={<DownloadIcon />}>
                  Exportar ruta
                </Button>
                <Button variant="p" icon={<RouteIcon />}>
                  Generar ruta de hoy
                </Button>
              </div>
            </div>

            <div className="grid g2" style={{ margin: '32px 0 16px' }}>
              <Card style={{ padding: '12px' }}>
                <div className="mapbox">
                  <Button className="xp" icon={<ExpandIcon />}>
                    Expandir
                  </Button>
                  <div className="map" style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span className="sm mut">Mapa Leaflet interactivo listo para despacho cartográfico</span>
                  </div>
                </div>
                <div className="row sp sm mut" style={{ padding: '12px 8px 4px' }}>
                  <span>14,8 km en total</span>
                  <span>285 L estimados</span>
                  <span>5 paradas</span>
                </div>
              </Card>

              <Card>
                <h2>Paradas Programadas</h2>
                <div style={{ marginTop: '14px' }}>
                  <div className="note" style={{ background: 'var(--nt)' }}>
                    <BellIcon />
                    <span>Alertas activas: <b>3</b> contenedores sobre el 80%</span>
                  </div>
                </div>
              </Card>
            </div>
          </section>
        )}

        {role === 'biz' && (
          <section id="biz">
            <div className="biz">
              <h1 style={{ marginBottom: '28px' }}>Pica Pollo Expreso</h1>
              <Card style={{ padding: '30px', textAlign: 'center' }}>
                <div className="ring">
                  <svg viewBox="0 0 130 130" width="190" height="190">
                    <circle cx="65" cy="65" r="54" fill="none" stroke="var(--nt)" strokeWidth="11" />
                    <circle
                      cx="65"
                      cy="65"
                      r="54"
                      fill="none"
                      stroke="#E0A81E"
                      strokeWidth="11"
                      strokeLinecap="round"
                      strokeDasharray="281.6 339.3"
                      transform="rotate(-90 65 65)"
                    />
                  </svg>
                  <b>83%<small>41,5 de 50 L</small></b>
                </div>
                <div className="row" style={{ justifyContent: 'center', marginTop: '20px' }}>
                  <ClockIcon style={{ color: 'var(--o)' }} />
                  <span>Recolección recomendada en unas <b>18 horas</b></span>
                </div>
              </Card>

              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', marginTop: '16px' }}>
                <StatWidget
                  icon={<TruckIcon />}
                  label="Última recolección"
                  value="28 oct"
                />
                <StatWidget
                  icon={<BatteryIcon />}
                  label="Sensor"
                  value="69%"
                />
              </div>

              <div className="note" style={{ marginTop: '16px' }}>
                <ShieldIcon />
                <span>Recolecciones verificadas · Ley 225-20</span>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
