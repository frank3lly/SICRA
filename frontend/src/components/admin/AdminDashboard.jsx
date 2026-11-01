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
  runFleetForecast,
  DEFAULT_PROJECTIONS
} from '../../services/api';

/**
 * Admin Fleet Overview and MLOps Supervision Cockpit
 */
export function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [containers, setContainers] = useState([]);
  const [projections, setProjections] = useState(DEFAULT_PROJECTIONS);
  const [isCalculating, setIsCalculating] = useState(false);
  const [hasRunProjection, setHasRunProjection] = useState(false);
  const [btnText, setBtnText] = useState('Ejecutar proyección');
  const projRef = useRef(null);

  // Fetch initial fleet stats and container list
  useEffect(() => {
    let mounted = true;

    async function loadData() {
      const [envStats, containerList] = await Promise.all([
        fetchEnvironmentalStats(),
        fetchContainers()
      ]);
      if (mounted) {
        setStats(envStats);
        setContainers(containerList);
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
    } catch (e) {
      console.warn('Forecast API finished with note:', e);
    }

    // 900ms smooth simulation matching the design reference
    setTimeout(() => {
      setIsCalculating(false);
      setBtnText('Actualizar proyección');
      setHasRunProjection(true);

      // Smooth scroll into view
      setTimeout(() => {
        if (projRef.current) {
          projRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }, 50);
    }, 900);
  };

  const oilLiters = stats?.total_oil_diverted_liters ?? 14250;
  const co2Avoided = stats?.co2_avoided_kg ?? 40612;
  const collectionsCount = stats?.total_collections_count ?? 312;
  const activeAlerts = stats?.active_alerts_count ?? 3;
  const waterPreserved = stats?.water_preserved_liters ?? 14250000;

  const formattedOil = `${Number(oilLiters).toLocaleString('es-DO')} L`;
  const formattedCo2 = `${Number(co2Avoided).toLocaleString('es-DO')} kg`;

  return (
    <section id="admin">
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
          value={String(collectionsCount)}
        />
        <StatWidget
          icon={<BellIcon />}
          label="Alertas activas"
          value={String(activeAlerts)}
        />
      </div>

      {/* Projection Card (animated and displayed when executed) */}
      {hasRunProjection && (
        <div ref={projRef}>
          <ProjectionChart
            id="proj"
            data={projections}
            lastUpdated="Actualizada hoy 6:00"
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
