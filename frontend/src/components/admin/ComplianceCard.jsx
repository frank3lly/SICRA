import React, { useState } from 'react';
import { Card, Chip, Button, LeafIcon, ShieldIcon } from '../common';
import { downloadAuditReportPdf } from '../../services/api';

/**
 * Environmental Traceability & Compliance Card
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
  const [downloading, setDownloading] = useState(false);
  const hasData = waterPreservedLiters !== null && waterPreservedLiters > 0;
  const formattedWater = hasData ? Number(waterPreservedLiters).toLocaleString('es-DO') : '0';

  const handleDownloadReport = async () => {
    try {
      setDownloading(true);
      await downloadAuditReportPdf();
    } catch (err) {
      console.error('Error downloading report PDF:', err);
      alert('Error al generar el reporte en PDF. Por favor verifica la conexión con el servidor.');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Card className={className} {...props}>
      <h2>Cumplimiento</h2>
      <span className="chip" style={{ display: 'inline-block', margin: '10px 0 18px' }}>
        Trazabilidad Verificada
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
        <Button
          variant="n"
          icon={<ShieldIcon />}
          onClick={handleDownloadReport}
          disabled={downloading}
        >
          {downloading ? 'Generando PDF…' : 'Descargar reporte'}
        </Button>
      </div>
    </Card>
  );
}

export default ComplianceCard;
