import React, { useState, useEffect } from 'react';
import { Card, StatWidget, TruckIcon, BatteryIcon } from '../common';
import { CircularRingGauge } from './CircularRingGauge';
import { HistoryTable } from './HistoryTable';
import { fetchMyContainer, fetchContainers } from '../../services/api';

/**
 * Business Owner Portal Component
 * Equips kitchen managers and food establishment operators with real-time oil levels,
 * sensor diagnostics, and statutory collection proof under Ley 225-20.
 */
export function BusinessDashboard() {
  const [containerData, setContainerData] = useState(null);
  const [availableBusinesses, setAvailableBusinesses] = useState([]);
  const [selectedBusinessId, setSelectedBusinessId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState(null);

  // Load available establishments for selector
  useEffect(() => {
    let mounted = true;

    async function loadEstablishments() {
      const res = await fetchContainers();
      if (mounted && res?.containers?.length > 0) {
        setAvailableBusinesses(res.containers);
      }
    }

    loadEstablishments();
    return () => {
      mounted = false;
    };
  }, []);

  // Fetch container data whenever selected business changes
  useEffect(() => {
    let mounted = true;
    setIsLoading(true);
    setErrorMessage(null);

    async function loadData() {
      const res = await fetchMyContainer(selectedBusinessId);
      if (mounted) {
        if (res.connected && res.data) {
          setContainerData(res.data);
        } else {
          setErrorMessage(res.error || 'No se pudo conectar con el servidor.');
        }
        setIsLoading(false);
      }
    }

    loadData();
    return () => {
      mounted = false;
    };
  }, [selectedBusinessId]);

  return (
    <section id="biz">
      <div className="biz">
        <div className="row sp" style={{ alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h1 style={{ margin: 0 }}>
              {containerData?.business_name || 'Pica Pollo Expreso'}
            </h1>
            {containerData?.business_address && (
              <div className="sm mut" style={{ marginTop: '4px' }}>
                {containerData.business_address} · San Pedro de Macorís
              </div>
            )}
          </div>

          {availableBusinesses.length > 1 && (
            <div style={{ minWidth: '200px' }}>
              <label htmlFor="biz-selector" className="sr-only" style={{ display: 'none' }}>
                Cambiar establecimiento
              </label>
              <select
                id="biz-selector"
                value={selectedBusinessId || containerData?.business_id || ''}
                onChange={(e) => setSelectedBusinessId(e.target.value)}
                style={{
                  background: 'var(--card)',
                  color: 'var(--ink)',
                  border: '1px solid var(--line)',
                  borderRadius: '8px',
                  padding: '7px 12px',
                  fontSize: '13px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  width: '100%'
                }}
              >
                {availableBusinesses.map((b) => (
                  <option key={b.business_id} value={b.business_id}>
                    {b.business_name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {errorMessage ? (
          <Card style={{ padding: '36px', textAlign: 'center', marginTop: '16px' }}>
            <div className="sm mut" style={{ color: 'var(--red)', marginBottom: '12px' }}>
              {errorMessage}
            </div>
            <button
              type="button"
              className="btn p"
              onClick={() => setSelectedBusinessId(selectedBusinessId)}
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
