import React, { useState, useEffect } from 'react';
import {
  StatWidget,
  Button,
  Card,
  DropIcon,
  CloudIcon,
  TruckIcon,
  BellIcon,
  SparkIcon,
  PlusIcon
} from '../common';
import { FleetTable } from './FleetTable';
import { ComplianceCard } from './ComplianceCard';
import { AddBusinessModal } from './AddBusinessModal';
import {
  fetchEnvironmentalStats,
  fetchContainers,
  fetchLatestPredictions,
  runFleetForecast
} from '../../services/api';

/**
 * Admin Fleet Overview
 * @param {function} onOpenForecast - Callback to open the full-page Forecast Center
 */
export function AdminDashboard({ onOpenForecast }) {
  const [stats, setStats] = useState(null);
  const [containers, setContainers] = useState([]);
  const [projections, setProjections] = useState([]);
  const [serverConnected, setServerConnected] = useState(true);
  const [isCalculating, setIsCalculating] = useState(false);
  const [btnText, setBtnText] = useState('Correr Proyección');
  const [isAddBusinessOpen, setIsAddBusinessOpen] = useState(false);
  const [successToast, setSuccessToast] = useState(null);

  const handleBusinessAdded = async (newBiz) => {
    setSuccessToast(`Comercio "${newBiz.name}" registrado exitosamente.`);
    setTimeout(() => setSuccessToast(null), 4000);

    const containerResult = await fetchContainers();
    if (containerResult.connected && containerResult.containers) {
      setContainers(containerResult.containers);
    }
  };

  // Load live data on mount
  useEffect(() => {
    let mounted = true;

    async function loadData() {
      const [envResult, containerResult, predResult] = await Promise.all([
        fetchEnvironmentalStats(),
        fetchContainers(),
        fetchLatestPredictions()
      ]);

      if (mounted) {
        const isConn = envResult.connected && containerResult.connected;
        setServerConnected(isConn);
        setStats(envResult);
        setContainers(containerResult.containers || []);

        if (predResult.projections && predResult.projections.length > 0) {
          setProjections(predResult.projections);
          setBtnText('Actualizar proyección');
        }
      }
    }

    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  const handleRunProjection = async () => {
    setIsCalculating(true);
    setBtnText('Calculando…');

    try {
      await runFleetForecast();
      setBtnText('Actualizar proyección');
      if (onOpenForecast) {
        onOpenForecast();
      }
    } catch (e) {
      console.error('Forecast failed:', e);
      alert('No se pudo ejecutar la proyección. Asegúrese de que el servidor backend esté activo.');
      setBtnText('Reintentar proyección');
    } finally {
      setIsCalculating(false);
    }
  };

  const oilLiters = stats?.total_oil_diverted_liters;
  const co2Avoided = stats?.co2_avoided_kg;
  const collectionsCount = stats?.total_collections_count;
  const waterPreserved = stats?.water_preserved_liters;

  // Real-time critical alerts count from containers and projections
  const activeAlerts = containers.filter(
    (c) => (c.current_fill_percentage ?? 0) >= 80 || (c.battery_percentage ?? 100) < 20
  ).length;

  const formattedOil = oilLiters !== null && oilLiters !== undefined
    ? `${Number(oilLiters).toLocaleString('es-DO')} L`
    : '—';
  const formattedCo2 = co2Avoided !== null && co2Avoided !== undefined
    ? `${Number(co2Avoided).toLocaleString('es-DO')} kg`
    : '—';
  const formattedCollections = collectionsCount !== null && collectionsCount !== undefined
    ? String(collectionsCount)
    : '—';
  const formattedAlerts = String(activeAlerts);

  const criticalForecastCount = projections.filter((p) => (p.forecastPct ?? 0) >= 80).length;

  return (
    <section id="admin">
      {!serverConnected && (
        <div
          className="note"
          style={{
            marginBottom: '20px',
            background: 'color-mix(in srgb, var(--yel) 18%, var(--card))',
            color: 'var(--ink)'
          }}
        >
          <BellIcon style={{ color: 'var(--yel)' }} />
          <span>
            <b>Atención:</b> No se pudo conectar con el servidor backend en <code>http://127.0.0.1:8000</code>. Sin datos en tiempo real.
          </span>
        </div>
      )}

      {/* Page Header */}
      <div className="row sp" style={{ alignItems: 'flex-end' }}>
        <div>
          <h1>Panorama de la flota</h1>
          <div className="sm mut" style={{ marginTop: '4px' }}>
            Monitoreo en tiempo real de {containers.length} comercios gastronómicos activos
          </div>
        </div>
        <div className="row" style={{ gap: '10px' }}>
          <Button
            id="run"
            variant="p"
            icon={<SparkIcon />}
            disabled={isCalculating}
            onClick={handleRunProjection}
          >
            <span>{isCalculating ? 'Calculando…' : btnText}</span>
          </Button>
          <Button icon={<PlusIcon />} onClick={() => setIsAddBusinessOpen(true)}>
            Nuevo comercio
          </Button>
        </div>
      </div>

      {/* Success Notification Banner */}
      {successToast && (
        <div
          className="note"
          style={{
            background: 'color-mix(in srgb, var(--g) 15%, transparent)',
            color: 'var(--g)',
            border: '1px solid color-mix(in srgb, var(--g) 30%, transparent)',
            margin: '20px 0 0',
            fontSize: '13px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <span>✓ {successToast}</span>
          <button
            type="button"
            onClick={() => setSuccessToast(null)}
            style={{
              background: 'none',
              border: 'none',
              color: 'inherit',
              cursor: 'pointer',
              fontWeight: 600,
              padding: '0 4px'
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Aggregate Metric Cards */}
      <div className="grid g4" style={{ margin: '28px 0 20px' }}>
        <StatWidget
          icon={<DropIcon />}
          label="Aceite desviado"
          value={formattedOil}
        />
        <StatWidget
          icon={<CloudIcon />}
          label="CO₂ evitado"
          value={formattedCo2}
        />
        <StatWidget
          icon={<TruckIcon />}
          label="Recolecciones"
          value={formattedCollections}
        />
        <StatWidget
          icon={<BellIcon />}
          label="Alertas activas"
          value={formattedAlerts}
        />
      </div>

      {/* Projections Spotlight Card */}
      <Card
        style={{
          marginBottom: '20px',
          padding: '24px 28px',
          background: 'linear-gradient(135deg, color-mix(in srgb, var(--g) 8%, var(--card)) 0%, var(--card) 100%)',
          border: '1.5px solid color-mix(in srgb, var(--g) 30%, transparent)'
        }}
      >
        <div className="row sp" style={{ gap: '16px' }}>
          <div className="row" style={{ gap: '16px', flex: 1, minWidth: '280px' }}>
            <img
              src="/assets/sicra-isotype.svg"
              alt="SICRA"
              style={{ width: '48px', height: '48px', flexShrink: 0 }}
            />
            <div>
              <h2 style={{ fontSize: '18px', marginBottom: '4px' }}>Proyecciones de Recolección</h2>
              <p className="sm mut" style={{ maxWidth: '65ch', margin: 0 }}>
                {criticalForecastCount > 0
                  ? `${criticalForecastCount} contenedores alcanzarán el 80% o más de llenado en las próximas 24 horas.`
                  : 'Estimación de llenado para anticipar las visitas y optimizar rutas.'}
              </p>
            </div>
          </div>
          <div className="row" style={{ gap: '10px' }}>
            <Button
              variant="p"
              icon={<SparkIcon />}
              onClick={onOpenForecast}
            >
              Ver proyecciones de flota
            </Button>
          </div>
        </div>
      </Card>

      {/* Compliance & Operations Summary Row */}
      <div className="grid g2" style={{ marginBottom: '20px' }}>
        <ComplianceCard
          waterPreservedLiters={waterPreserved}
          oilDivertedLiters={oilLiters}
          co2AvoidedKg={co2Avoided}
        />

        <Card>
          <h2>Operación Logística</h2>
          <span className="chip" style={{ display: 'inline-block', margin: '10px 0 18px' }}>
            Red Piloto SPM
          </span>
          <div className="note" style={{ background: 'var(--nt)' }}>
            <TruckIcon />
            <span>
              {containers.length || 11} comercios monitoreados en San Pedro de Macorís con telemetría activa y calibración de tara.
            </span>
          </div>
          <div style={{ marginTop: '18px' }}>
            <Button onClick={onOpenForecast} icon={<SparkIcon />}>
              Ver proyecciones
            </Button>
          </div>
        </Card>
      </div>

      {/* Full-Width Fleet Table */}
      <FleetTable containers={containers} />

      {/* Modal for adding new business */}
      <AddBusinessModal
        isOpen={isAddBusinessOpen}
        onClose={() => setIsAddBusinessOpen(false)}
        onSuccess={handleBusinessAdded}
      />
    </section>
  );
}

export default AdminDashboard;
