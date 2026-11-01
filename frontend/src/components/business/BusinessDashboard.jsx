import React, { useState, useEffect } from 'react';
import { Card, StatWidget, TruckIcon, BatteryIcon } from '../common';
import { CircularRingGauge } from './CircularRingGauge';
import { HistoryTable } from './HistoryTable';
import { fetchMyContainer } from '../../services/api';

/**
 * Business Owner Portal Component
 * Equips kitchen managers and food establishment operators with real-time oil levels,
 * sensor diagnostics, and verified collection custody receipts.
 */
export function BusinessDashboard() {
  const [containerData, setContainerData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState(null);

  const loadData = async () => {
    setIsLoading(true);
    setErrorMessage(null);

    const res = await fetchMyContainer();
    if (res.connected && res.data) {
      setContainerData(res.data);
    } else {
      setErrorMessage(res.error || 'No se pudo conectar con el servidor.');
    }
    setIsLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <section id="biz">
      <div className="biz">
        <div style={{ marginBottom: '24px' }}>
          <h1 style={{ margin: 0 }}>
            {containerData?.business_name || 'Mi Establecimiento'}
          </h1>
          {containerData?.business_address && (
            <div className="sm mut" style={{ marginTop: '6px' }}>
              {containerData.business_address} · San Pedro de Macorís
            </div>
          )}
        </div>

        {isLoading ? (
          <Card style={{ padding: '40px', textAlign: 'center' }}>
            <div className="sm mut">Cargando estado del contenedor…</div>
          </Card>
        ) : errorMessage ? (
          <Card style={{ padding: '36px', textAlign: 'center' }}>
            <div className="sm mut" style={{ color: 'var(--red)', marginBottom: '12px' }}>
              {errorMessage}
            </div>
            <button
              type="button"
              className="btn p"
              onClick={loadData}
            >
              Reintentar conexión
            </button>
          </Card>
        ) : (
          <>
            {/* Animated Circular Progress Ring Gauge */}
            <CircularRingGauge
              percentage={containerData?.current_fill_percentage ?? 0}
              currentVolume={containerData?.current_volume_liters ?? 0}
              capacity={containerData?.capacity_liters ?? 50}
              hoursRemaining={containerData?.hours_to_collection}
            />

            {/* Hardware Sensor & Last Collection Cards */}
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', marginTop: '16px' }}>
              <StatWidget
                icon={<TruckIcon />}
                label="Última recolección"
                value={containerData?.last_pickup_date || '26 oct'}
              />
              <StatWidget
                icon={<BatteryIcon />}
                label="Sensor"
                value={`${Math.round(containerData?.battery_percentage ?? 83)}%`}
              />
            </div>

            {/* Historical Custody Proof Table */}
            <HistoryTable pickups={containerData?.pickups || []} />
          </>
        )}
      </div>
    </section>
  );
}

export default BusinessDashboard;
