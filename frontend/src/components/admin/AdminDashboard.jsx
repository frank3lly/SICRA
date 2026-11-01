import React, { useState, useEffect, useRef } from 'react';
import {
  StatWidget,
  Button,
  DropIcon,
  CloudIcon,
  TruckIcon,
  BellIcon,
  SparkIcon,
  PlusIcon
} from '../common';
import { ProjectionChart } from './ProjectionChart';
import { FleetTable } from './FleetTable';
import { ComplianceCard } from './ComplianceCard';
import {
  fetchEnvironmentalStats,
  fetchContainers,
  fetchLatestPredictions,
  runFleetForecast
} from '../../services/api';

/**
 * Admin Fleet Overview and MLOps Supervision Cockpit
 * Displays live data from FastAPI / SQLite. Indicates when data is unavailable or empty without fake mocks.
 */
export function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [containers, setContainers] = useState([]);
  const [projections, setProjections] = useState([]);
  const [lastProjectionTime, setLastProjectionTime] = useState('Sin proyecciones aún');
  const [serverConnected, setServerConnected] = useState(true);
  const [isCalculating, setIsCalculating] = useState(false);
  const [showProjectionCard, setShowProjectionCard] = useState(false);
  const [btnText, setBtnText] = useState('Ejecutar proyección');
  const projRef = useRef(null);

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
          setLastProjectionTime('Actualizada con modelo predictivo');
          setShowProjectionCard(true);
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
      const res = await runFleetForecast();
      if (res.projections && res.projections.length > 0) {
        setProjections(res.projections);
      }
      setLastProjectionTime(`Actualizada ${new Date().toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit' })}`);
      setBtnText('Actualizar proyección');
      setShowProjectionCard(true);

      setTimeout(() => {
        if (projRef.current) {
          projRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }, 50);
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
  const activeAlerts = stats?.active_alerts_count;
  const waterPreserved = stats?.water_preserved_liters;

  const formattedOil = oilLiters !== null && oilLiters !== undefined
    ? `${Number(oilLiters).toLocaleString('es-DO')} L`
    : '—';
  const formattedCo2 = co2Avoided !== null && co2Avoided !== undefined
    ? `${Number(co2Avoided).toLocaleString('es-DO')} kg`
    : '—';
  const formattedCollections = collectionsCount !== null && collectionsCount !== undefined
    ? String(collectionsCount)
    : '—';
  const formattedAlerts = activeAlerts !== null && activeAlerts !== undefined
    ? String(activeAlerts)
    : '—';

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
            <b>Atención:</b> No se pudo conectar con el servidor backend en <code>http://127.0.0.1:8000</code>. Los datos mostrados reflejan que no hay conexión activa.
          </span>
        </div>
      )}

      <div className="row sp" style={{ alignItems: 'flex-end' }}>
        <div>
          <h1>Panorama de la flota</h1>
        </div>
        <div className="row">
          <Button
            id="run"
            icon={<SparkIcon />}
            disabled={isCalculating}
            onClick={handleRunProjection}
          >
            <span>{btnText}</span>
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

      {/* Projection Card: Displays live predictions from ML inference or empty indicator */}
      {showProjectionCard && (
        <div ref={projRef}>
          <ProjectionChart
            id="proj"
            data={projections}
            lastUpdated={lastProjectionTime}
          />
        </div>
      )}

      <div className="grid g2">
        <FleetTable containers={containers} />
        <ComplianceCard
          waterPreservedLiters={waterPreserved}
          oilDivertedLiters={oilLiters}
          co2AvoidedKg={co2Avoided}
        />
      </div>
    </section>
  );
}

export default AdminDashboard;
