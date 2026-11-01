import React from 'react';
import { Card, ShieldIcon } from '../common';

/**
 * Historical Pickups Custody Table
 * Displays verified collection events and custody receipts
 *
 * @param {Array<object>} pickups - Array of collection events: [{ date, collector_agency, liters }]
 */
export function HistoryTable({ pickups = [] }) {
  return (
    <>
      <Card style={{ marginTop: '16px' }}>
        <h2>Historial</h2>

        {pickups.length === 0 ? (
          <div
            className="sm mut"
            style={{
              padding: '24px 12px',
              textAlign: 'center',
              color: 'var(--mut)'
            }}
          >
            No hay recolecciones previas registradas para este contenedor.
          </div>
        ) : (
          <table style={{ marginTop: '10px', width: '100%', borderCollapse: 'collapse' }}>
            <tbody>
              {pickups.map((p, idx) => (
                <tr key={p.id || idx}>
                  <td style={{ padding: '10px 8px', color: 'var(--ink)' }}>{p.date}</td>
                  <td style={{ padding: '10px 8px', color: 'var(--mut)' }}>
                    {p.collector_agency || 'Reoil Dominicana'}
                  </td>
                  <td
                    style={{
                      padding: '10px 8px',
                      textAlign: 'right',
                      fontWeight: 600,
                      color: 'var(--ink)'
                    }}
                  >
                    {String(p.liters).replace('.', ',')} L
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <div className="note" style={{ marginTop: '16px' }}>
        <ShieldIcon />
        <span>Recolecciones y pesajes verificados</span>
      </div>
    </>
  );
}

export default HistoryTable;
