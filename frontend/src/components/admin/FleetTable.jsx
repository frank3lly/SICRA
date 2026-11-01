import React from 'react';
import { Card, ProgressBar, Chip } from '../common';

/**
 * Fleet Containers Table matching `.scroll table` in reference
 * @param {Array<object>} containers - List of container records
 */
export function FleetTable({ containers = [], className = '', ...props }) {
  return (
    <Card className={className} {...props}>
      <div className="row sp" style={{ marginBottom: '14px' }}>
        <h2>Contenedores</h2>
        <span className="sm mut">{containers.length} activos</span>
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
            {containers.map((container) => {
              const fillPct = container.current_fill_percentage ?? 0;
              const batteryPct = container.battery_percentage ?? 85;

              // Determine status label & chip variant
              let statusLabel = container.status_label;
              let statusVariant = container.status_variant;

              if (!statusLabel) {
                if (batteryPct < 20) {
                  statusLabel = 'Batería baja';
                  statusVariant = 'w';
                } else if (fillPct >= 95) {
                  statusLabel = 'Crítico';
                  statusVariant = 'c';
                } else if (fillPct >= 80) {
                  statusLabel = 'Casi lleno';
                  statusVariant = 'w';
                } else {
                  statusLabel = 'Normal';
                  statusVariant = '';
                }
              }

              return (
                <tr key={container.id || container.business_name}>
                  <td>{container.business_name}</td>
                  <td>
                    <div className="row" style={{ flexWrap: 'nowrap', gap: '8px' }}>
                      <ProgressBar value={fillPct} />
                      <span style={{ minWidth: '34px', textAlign: 'right' }}>
                        {fillPct}%
                      </span>
                    </div>
                  </td>
                  <td>{batteryPct}%</td>
                  <td>
                    <Chip variant={statusVariant}>{statusLabel}</Chip>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export default FleetTable;
