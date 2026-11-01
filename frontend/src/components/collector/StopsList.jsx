import React from 'react';
import { Card, Chip, Button, CheckIcon, BellIcon } from '../common';

/**
 * Sequenced Stops List with Pickup Confirmation
 * @param {Array<object>} stops - List of stops (excluding depot)
 * @param {function} onConfirm - Callback to confirm container pickup
 * @param {string} confirmingId - ID of stop currently being confirmed (loading state)
 * @param {number} activeAlertsCount - Count of fleet containers over 80%
 */
export function StopsList({
  stops = [],
  onConfirm,
  confirmingId = null,
  activeAlertsCount = 0
}) {
  return (
    <Card>
      <div className="row sp" style={{ marginBottom: '12px' }}>
        <h2>Paradas Programadas</h2>
        <span className="sm mut">
          {stops.filter((s) => s.visited).length} de {stops.length} recolectadas
        </span>
      </div>

      {stops.length === 0 ? (
        <div
          className="note"
          style={{
            background: 'var(--nt)',
            color: 'var(--mut)',
            padding: '24px',
            textAlign: 'center',
            justifyContent: 'center',
            marginTop: '8px'
          }}
        >
          No hay paradas en la ruta actual. Presione "Generar ruta de hoy" para calcular las paradas prioritarias.
        </div>
      ) : (
        <div id="stops" style={{ marginTop: '8px' }}>
          {stops.map((stop, index) => {
            const isDone = Boolean(stop.visited);
            const stopNumber = index + 1;
            const isConfirming = confirmingId === stop.business_id;

            return (
              <div
                key={stop.business_id || index}
                className={`stop ${isDone ? 'done' : ''}`}
              >
                <div className="n-dot">
                  {isDone ? (
                    <CheckIcon style={{ width: '15px', height: '15px' }} />
                  ) : (
                    stopNumber
                  )}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="t" style={{ fontWeight: 500 }}>
                    {stop.business_name}
                  </div>
                  <div className="sm mut" style={{ wordBreak: 'break-word' }}>
                    {stop.address} {stop.estimated_liters ? `· ${stop.estimated_liters} L est.` : ''}
                  </div>
                </div>

                {isDone ? (
                  <Chip>Vaciado</Chip>
                ) : (
                  <Button
                    size="sm"
                    disabled={isConfirming}
                    onClick={() => onConfirm && onConfirm(stop.business_id)}
                    icon={<CheckIcon />}
                  >
                    <span>{isConfirming ? 'Registrando…' : 'Confirmar'}</span>
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="note" style={{ marginTop: '16px', background: 'var(--nt)' }}>
        <BellIcon />
        <span>
          Alertas activas: <b>{activeAlertsCount}</b> contenedores sobre el 80%
        </span>
      </div>
    </Card>
  );
}

export default StopsList;
