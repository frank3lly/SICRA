import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Chip,
  SegmentedControl,
  StatWidget,
  SparkIcon,
  BellIcon,
  DropIcon,
  CloudIcon,
  ClockIcon
} from '../common';
import { runFleetForecast, fetchLatestPredictions } from '../../services/api';

const PAGE_SIZE = 11;

const getBarColor = (pct) => {
  if (pct >= 95) return 'var(--red)';
  if (pct >= 80) return 'var(--yel)';
  return 'var(--g)';
};

/**
 * Dedicated Full-Page Forecast View with Search and 11-Item Pagination
 * @param {function} onBack - Handler to return to the fleet overview
 * @param {Array<object>} initialProjections - Initial predictions from server
 */
export function ForecastCenter({ onBack, initialProjections = [] }) {
  const [projections, setProjections] = useState(initialProjections);
  const [mode, setMode] = useState('p'); // 'p' = 24h fill %, 'l' = daily liters, 'h' = hours to 80%
  const [sortBy, setSortBy] = useState('urgency'); // 'urgency', 'volume', 'name'
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [isRecalculating, setIsRecalculating] = useState(false);
  const [lastCalculated, setLastCalculated] = useState('Reciente');
  const [animated, setAnimated] = useState(false);

  // Fetch latest projections on load if empty
  useEffect(() => {
    let mounted = true;
    if (projections.length === 0) {
      fetchLatestPredictions().then((res) => {
        if (mounted && res.projections && res.projections.length > 0) {
          setProjections(res.projections);
          setLastCalculated(new Date().toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit' }));
        }
      });
    }
    return () => {
      mounted = false;
    };
  }, []);

  // Animation trigger on mode, sort, or pagination change
  useEffect(() => {
    setAnimated(false);
    const timer = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setAnimated(true);
      });
    });
    return () => cancelAnimationFrame(timer);
  }, [mode, sortBy, currentPage, searchQuery]);

  // Reset page when searching
  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
    setCurrentPage(1);
  };

  const handleRecalculate = async () => {
    setIsRecalculating(true);
    try {
      const res = await runFleetForecast();
      if (res.projections && res.projections.length > 0) {
        setProjections(res.projections);
      }
      setLastCalculated(new Date().toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit' }));
    } catch (err) {
      console.error('Error running forecast:', err);
      alert('No se pudo recalcular la proyección. Verifique la conexión con el servidor.');
    } finally {
      setIsRecalculating(false);
    }
  };

  // Sorting
  const sortedData = [...projections].sort((a, b) => {
    if (sortBy === 'urgency') {
      return (b.forecastPct ?? 0) - (a.forecastPct ?? 0);
    }
    if (sortBy === 'volume') {
      return (b.dailyLiters ?? 0) - (a.dailyLiters ?? 0);
    }
    return (a.name || '').localeCompare(b.name || '');
  });

  // Search filtering
  const filteredData = sortedData.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const nameMatch = (item.name || '').toLowerCase().includes(q);
    const addressMatch = (item.address || '').toLowerCase().includes(q);
    const cityMatch = (item.city || '').toLowerCase().includes(q);
    return nameMatch || addressMatch || cityMatch;
  });

  // Pagination (Strictly max 11 at a time)
  const totalItems = filteredData.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * PAGE_SIZE;
  const endIndex = Math.min(startIndex + PAGE_SIZE, totalItems);
  const paginatedTableItems = filteredData.slice(startIndex, endIndex);

  // Top items for visual chart (capped at max 11 for clarity)
  const chartItems = sortedData.slice(0, PAGE_SIZE);

  // Aggregate Metrics across all records
  const criticalContainers = projections.filter((p) => (p.forecastPct ?? 0) >= 80);
  const overflowImminent = projections.filter((p) => (p.forecastPct ?? 0) >= 95);
  const totalProjectedLiters = projections.reduce((acc, p) => acc + (p.dailyLiters || 0), 0);
  const avgDailyLiters = projections.length > 0 ? (totalProjectedLiters / projections.length).toFixed(1) : '0';

  const pendingCritical = projections
    .filter((p) => typeof p.hoursTo80 === 'number' && p.hoursTo80 > 0)
    .sort((a, b) => a.hoursTo80 - b.hoursTo80);
  const nextCriticalStop = pendingCritical.length > 0
    ? `${pendingCritical[0].hoursTo80} h · ${pendingCritical[0].name.split('-')[0].trim()}`
    : overflowImminent.length > 0
    ? '¡Recolección Inmediata!'
    : 'Flota con espacio';

  return (
    <div className="forecast-page">
      {/* Top Navigation & Return Action */}
      <div className="row sp" style={{ marginBottom: '20px' }}>
        <Button onClick={onBack} icon={<span style={{ fontSize: '16px', lineHeight: 1 }}>←</span>}>
          Volver al panorama de flota
        </Button>
        <div className="row" style={{ gap: '10px' }}>
          <span className="chip">Actualizado: {lastCalculated}</span>
          <Button
            variant="p"
            icon={<SparkIcon />}
            disabled={isRecalculating}
            onClick={handleRecalculate}
          >
            <span>{isRecalculating ? 'Calculando...' : 'Recalcular proyecciones'}</span>
          </Button>
        </div>
      </div>

      {/* Header */}
      <div className="forecast-header">
        <h1>Proyecciones de Recolección</h1>
        <p className="lead" style={{ margin: '8px 0 24px', maxWidth: '75ch' }}>
          Estimación anticipada de volumen y niveles de llenado en 24 horas para optimizar las rutas de recogida.
        </p>
      </div>

      {/* KPI Grid */}
      <div className="forecast-kpi-grid">
        <StatWidget
          icon={<BellIcon style={{ color: overflowImminent.length > 0 ? 'var(--red)' : 'var(--yel)' }} />}
          label="Alertas Críticas (≤ 24 h)"
          value={String(criticalContainers.length)}
        />
        <StatWidget
          icon={<DropIcon />}
          label="Generación Estimada (Flota)"
          value={`${totalProjectedLiters.toFixed(1)} L/día`}
        />
        <StatWidget
          icon={<CloudIcon />}
          label="Tasa Promedio por Local"
          value={`${avgDailyLiters} L/día`}
        />
        <StatWidget
          icon={<ClockIcon style={{ color: 'var(--o)' }} />}
          label="Próximo Umbral Crítico (80%)"
          value={nextCriticalStop}
        />
      </div>

      {/* Visualizer Card (Visualizes top 11 items) */}
      <Card style={{ marginBottom: '24px', padding: '28px' }}>
        <div className="row sp" style={{ marginBottom: '20px' }}>
          <div>
            <h2>Pronóstico de la Flota</h2>
            <div className="sm mut">
              Comparativa de los {chartItems.length} comercios más prioritarios de la red.
            </div>
          </div>

          <div className="row" style={{ gap: '12px' }}>
            <SegmentedControl
              id="fseg"
              value={mode}
              onChange={(newMode) => setMode(newMode)}
              options={[
                { value: 'p', label: 'Llenado en 24 h (%)' },
                { value: 'l', label: 'Volumen Diario (L)' },
                { value: 'h', label: 'Horas al 80%' }
              ]}
            />
          </div>
        </div>

        {/* Order Selector */}
        <div className="row sp sm mut" style={{ padding: '8px 0', borderBottom: '1px solid var(--line)', marginBottom: '16px' }}>
          <span>
            Mostrando <b>{chartItems.length} de {sortedData.length} comercios</b> según prioridad
          </span>
          <div className="row" style={{ gap: '8px' }}>
            <span>Ordenar por:</span>
            <button
              type="button"
              className={`chip ${sortBy === 'urgency' ? 'w' : ''}`}
              style={{ cursor: 'pointer', border: 0 }}
              onClick={() => setSortBy('urgency')}
            >
              Mayor Urgencia (%)
            </button>
            <button
              type="button"
              className={`chip ${sortBy === 'volume' ? 'w' : ''}`}
              style={{ cursor: 'pointer', border: 0 }}
              onClick={() => setSortBy('volume')}
            >
              Mayor Volumen (L)
            </button>
            <button
              type="button"
              className={`chip ${sortBy === 'name' ? 'w' : ''}`}
              style={{ cursor: 'pointer', border: 0 }}
              onClick={() => setSortBy('name')}
            >
              Nombre
            </button>
          </div>
        </div>

        {chartItems.length === 0 ? (
          <div
            className="note"
            style={{
              padding: '36px',
              textAlign: 'center',
              justifyContent: 'center',
              background: 'var(--nt)'
            }}
          >
            No hay proyecciones almacenadas en el servidor. Presione "Recalcular proyecciones" para generar el pronóstico.
          </div>
        ) : (
          <>
            <div className="plot" style={{ height: '240px' }}>
              {mode === 'p' && (
                <div className="thr">
                  <em>80% Umbral Crítico</em>
                </div>
              )}

              {chartItems.map((item, idx) => {
                const currentPct = item.currentPct ?? 0;
                const forecastPct = item.forecastPct ?? 0;
                const dailyL = item.dailyLiters ?? 0;
                const hours = item.hoursTo80 ?? 0;

                if (mode === 'p') {
                  const currentHeight = Math.min(Math.max(currentPct, 0), 100);
                  const forecastHeight = Math.min(Math.max(forecastPct, 0), 100);
                  const forecastColor = getBarColor(forecastPct);

                  return (
                    <div key={item.container_id || idx} className="col">
                      <div className="pair">
                        <div
                          className="b"
                          title={`Actual: ${currentPct}%`}
                          style={{
                            background: 'color-mix(in srgb, var(--ink) 16%, var(--card))',
                            height: animated ? `${currentHeight}%` : '0%'
                          }}
                        >
                          <span>{currentPct}%</span>
                        </div>
                        <div
                          className="b"
                          title={`En 24h: ${forecastPct}%`}
                          style={{
                            background: forecastColor,
                            height: animated ? `${forecastHeight}%` : '0%'
                          }}
                        >
                          <span>{forecastPct}%</span>
                        </div>
                      </div>
                    </div>
                  );
                }

                if (mode === 'l') {
                  const maxLitersScale = 35;
                  const heightPct = Math.min((dailyL / maxLitersScale) * 100, 100);
                  return (
                    <div key={item.container_id || idx} className="col">
                      <div
                        className="b"
                        title={`${dailyL} Litros/día`}
                        style={{
                          background: 'var(--g)',
                          height: animated ? `${heightPct}%` : '0%'
                        }}
                      >
                        <span>{String(dailyL).replace('.', ',')} L</span>
                      </div>
                    </div>
                  );
                }

                const maxHoursScale = 96;
                const validHours = Math.max(0, hours);
                const heightPct = Math.min((validHours / maxHoursScale) * 100, 100);
                const barColor = validHours === 0 ? 'var(--red)' : validHours < 24 ? 'var(--yel)' : 'var(--g)';

                return (
                  <div key={item.container_id || idx} className="col">
                    <div
                      className="b"
                      title={`${validHours} horas`}
                      style={{
                        background: barColor,
                        height: animated ? `${heightPct}%` : '0%'
                      }}
                    >
                      <span>{validHours === 0 ? '¡Alerta!' : `${validHours}h`}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="labs">
              {chartItems.map((item, idx) => (
                <div key={item.container_id || idx} style={{ fontSize: '11px', lineHeight: 1.25 }}>
                  {item.name.replace('San Pedro', '').replace('Macorís', '').trim()}
                </div>
              ))}
            </div>

            {mode === 'p' && (
              <div
                className="row sm mut"
                style={{ justifyContent: 'center', marginTop: '18px', gap: '24px' }}
              >
                <span className="row" style={{ gap: '6px' }}>
                  <i className="sw" style={{ background: 'color-mix(in srgb, var(--ink) 16%, var(--card))' }} />
                  Hoy
                </span>
                <span className="row" style={{ gap: '6px' }}>
                  <i className="sw" style={{ background: 'var(--g)' }} />
                  En 24 h (&lt; 80%)
                </span>
                <span className="row" style={{ gap: '6px' }}>
                  <i className="sw" style={{ background: 'var(--yel)' }} />
                  Alerta (80–94%)
                </span>
                <span className="row" style={{ gap: '6px' }}>
                  <i className="sw" style={{ background: 'var(--red)' }} />
                  Crítico (≥ 95%)
                </span>
              </div>
            )}
          </>
        )}
      </Card>

      {/* Detail Table with Searchbar and 11-Item Pagination */}
      <Card style={{ padding: '28px' }}>
        <div className="row sp" style={{ marginBottom: '18px', gap: '16px' }}>
          <div>
            <h2>Detalle por Comercio</h2>
            <div className="sm mut">
              Estimación de llenado y horas restantes para planificar las visitas de recolección.
            </div>
          </div>

          {/* Searchbar */}
          <div className="search-box">
            <svg
              className="i"
              viewBox="0 0 24 24"
              style={{ width: '16px', height: '16px', color: 'var(--mut)' }}
            >
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" fill="none" />
              <line x1="16" y1="16" x2="21" y2="21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            <input
              type="text"
              className="search-input"
              placeholder="Buscar comercio o dirección…"
              value={searchQuery}
              onChange={handleSearchChange}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setCurrentPage(1);
                }}
                style={{
                  border: 0,
                  background: 'none',
                  cursor: 'pointer',
                  color: 'var(--mut)',
                  fontSize: '13px'
                }}
              >
                ✕
              </button>
            )}
          </div>
        </div>

        <div className="scroll">
          <table className="forecast-matrix-table">
            <thead>
              <tr>
                <th>Comercio</th>
                <th>Capacidad y Nivel Actual</th>
                <th>Proyección en 24 h</th>
                <th>Generación Diaria Est.</th>
                <th>Horas hasta el 80%</th>
                <th style={{ textAlign: 'right' }}>Prioridad de Recolección</th>
              </tr>
            </thead>
            <tbody>
              {paginatedTableItems.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '36px', color: 'var(--mut)' }}>
                    {searchQuery ? `No se encontraron comercios que coincidan con "${searchQuery}".` : 'No hay datos disponibles.'}
                  </td>
                </tr>
              ) : (
                paginatedTableItems.map((item) => {
                  const currentPct = Math.round(item.currentPct ?? 0);
                  const forecastPct = Math.round(item.forecastPct ?? 0);
                  const dailyL = item.dailyLiters ?? 0;
                  const hours = item.hoursTo80;
                  const currentVol = item.currentVolumeLiters ?? Math.round((currentPct / 100) * (item.capacityLiters || 50));
                  const capacity = item.capacityLiters ?? 50;

                  let priorityLabel = 'Normal';
                  let priorityVariant = '';
                  if (forecastPct >= 95 || hours === 0) {
                    priorityLabel = 'Inmediata (< 12h)';
                    priorityVariant = 'c';
                  } else if (forecastPct >= 80 || (typeof hours === 'number' && hours <= 24)) {
                    priorityLabel = 'Próximas 24 h';
                    priorityVariant = 'w';
                  }

                  return (
                    <tr key={item.container_id || item.name}>
                      <td className="business-name-cell">
                        <div style={{ fontWeight: 600, color: 'var(--ink)' }}>{item.name}</div>
                        <div className="sm mut">{item.address || 'San Pedro de Macorís'}</div>
                      </td>
                      <td>
                        <div className="row" style={{ flexWrap: 'nowrap', gap: '8px' }}>
                          <div className="bar" style={{ width: '90px' }}>
                            <i
                              className={currentPct >= 95 ? 'c' : currentPct >= 80 ? 'w' : ''}
                              style={{ width: `${currentPct}%` }}
                            />
                          </div>
                          <span style={{ fontVariantNumeric: 'tabular-nums', fontSize: '13px' }}>
                            {currentVol} / {capacity} L ({currentPct}%)
                          </span>
                        </div>
                      </td>
                      <td>
                        <div className="row" style={{ flexWrap: 'nowrap', gap: '8px' }}>
                          <div className="bar" style={{ width: '90px' }}>
                            <i
                              className={forecastPct >= 95 ? 'c' : forecastPct >= 80 ? 'w' : ''}
                              style={{ width: `${forecastPct}%` }}
                            />
                          </div>
                          <span
                            style={{
                              fontWeight: 600,
                              fontVariantNumeric: 'tabular-nums',
                              color: forecastPct >= 95 ? 'var(--red)' : forecastPct >= 80 ? 'var(--yel)' : 'var(--g)'
                            }}
                          >
                            {forecastPct}%
                          </span>
                        </div>
                      </td>
                      <td style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>
                        +{String(dailyL).replace('.', ',')} L/día
                      </td>
                      <td>
                        {hours === 0 ? (
                          <span className="time-to-critical urgent">¡Ya superado!</span>
                        ) : typeof hours === 'number' && hours > 0 ? (
                          <span className={`time-to-critical ${hours <= 24 ? 'warning' : 'safe'}`}>
                            {hours} horas
                          </span>
                        ) : (
                          <span className="sm mut">—</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <Chip variant={priorityVariant}>{priorityLabel}</Chip>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar (Max 11 per page) */}
        {totalItems > 0 && (
          <div className="pagination-bar">
            <span className="sm mut">
              Página <b>{safeCurrentPage}</b> de <b>{totalPages}</b> · Mostrando{' '}
              <b>{startIndex + 1}–{endIndex}</b> de <b>{totalItems}</b> comercios
            </span>

            <div className="row" style={{ gap: '8px' }}>
              <button
                type="button"
                className="pagination-btn"
                disabled={safeCurrentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              >
                ← Anterior
              </button>
              <button
                type="button"
                className="pagination-btn"
                disabled={safeCurrentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              >
                Siguiente →
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

export default ForecastCenter;
