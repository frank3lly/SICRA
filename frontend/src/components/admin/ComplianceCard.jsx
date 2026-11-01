import React from 'react';
import { Card, Chip, Button, LeafIcon, ShieldIcon } from '../common';

/**
 * Compliance with Dominican Solid Waste Law 225-20 Card
 * @param {number|null} waterPreservedLiters - Total potable water preserved in liters
 * @param {number|null} oilDivertedLiters - Total cooking oil diverted in liters
 * @param {number|null} co2AvoidedKg - Total CO2 equivalent avoided in kg
 */
export function ComplianceCard({
  waterPreservedLiters = 0,
  oilDivertedLiters = 0,
  co2AvoidedKg = 0,
  className = '',
  ...props
}) {
  const hasData = waterPreservedLiters !== null && waterPreservedLiters > 0;
  const formattedWater = hasData ? Number(waterPreservedLiters).toLocaleString('es-DO') : '0';

  const handleDownloadReport = () => {
    if (!hasData) {
      alert('No hay datos registrados aún para generar el reporte de cumplimiento.');
      return;
    }

    const reportContent = [
      'REPORTE DE AUDITORÍA Y CUMPLIMIENTO AMBIENTAL - SICRA',
      'Marco Legal: Ley No. 225-20 de Gestión Integral y Coprocesamiento de Residuos',
      `Fecha de Emisión: ${new Date().toLocaleDateString('es-DO')}`,
      '------------------------------------------------------------',
      `Aceite Vegetal Usado Desviado: ${Number(oilDivertedLiters || 0).toLocaleString('es-DO')} Litros`,
      `Agua Potable Preservada: ${formattedWater} Litros (Factor: 1 L aceite = 1,000 L agua)`,
      `Emisiones de CO2 Evitadas: ${Number(co2AvoidedKg || 0).toLocaleString('es-DO')} kg CO2e`,
      'Estado: Conforme con la normativa ambiental dominicana'
    ].join('\n');

    const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `reporte_cumplimiento_ley_225_20_${new Date().toISOString().slice(0, 10)}.txt`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <Card className={className} {...props}>
      <h2>Cumplimiento</h2>
      <span className="chip" style={{ display: 'inline-block', margin: '10px 0 18px' }}>
        Ley 225-20
      </span>
      <div className="note">
        <LeafIcon />
        <span>
          {hasData
            ? `${formattedWater} L de agua preservados por el aceite que no llegó al drenaje.`
            : 'Sin registros de recolección acumulados aún en el sistema.'}
        </span>
      </div>
      <div style={{ marginTop: '18px' }}>
        <Button variant="n" icon={<ShieldIcon />} onClick={handleDownloadReport} disabled={!hasData}>
          Descargar reporte
        </Button>
      </div>
    </Card>
  );
}

export default ComplianceCard;
