import React, { useState, useEffect, useRef } from 'react';
import { Card, Chip, SegmentedControl, BellIcon } from '../common';

/**
 * Helper to determine bar color based on percentage threshold
 */
const getBarColor = (pct) => {
  if (pct >= 95) return 'var(--red)';
  if (pct >= 80) return 'var(--yel)';
  return 'var(--g)';
};

/**
 * Interactive Projection Bar Chart with 80% Threshold
 * @param {Array<{name: string, dailyLiters: number, currentPct: number, forecastPct: number}>} data
 * @param {string} lastUpdated
 */
export function ProjectionChart({
  data = [],
  lastUpdated = 'Actualizada hoy 6:00',
  className = '',
  ...props
}) {
  const [mode, setMode] = useState('l'); // 'l' = Litros por día, 'p' = Llenado en 24 h
  const [animated, setAnimated] = useState(false);
  const plotRef = useRef(null);

  // Trigger smooth height transition on mode change or data change
  useEffect(() => {
    setAnimated(false);
    const animTimer = requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setAnimated(true);
      });
    });
    return () => cancelAnimationFrame(animTimer);
  }, [mode, data]);

  const criticalCount = data.filter((item) => item.forecastPct >= 95).length;
  const isLitersMode = mode === 'l';

  return (
    <Card className={`proj-card ${className}`.trim()} style={{ marginBottom: '16px' }} {...props}>
      <div className="row sp">
        <div className="row">
          <h2>Proyección</h2>
          <Chip>{lastUpdated}</Chip>
        </div>
        <SegmentedControl
          id="pseg"
          value={mode}
          onChange={(newMode) => setMode(newMode)}
          options={[
            { value: 'l', label: 'Litros por día' },
            { value: 'p', label: 'Llenado en 24 h' }
          ]}
        />
      </div>

      <div className="note" style={{ marginTop: '16px' }}>
        <BellIcon />
        <span>
          {criticalCount} contenedores superarán el 95% en las próximas 24 h
        </span>
      </div>

      <div className="plot" id="plot" ref={plotRef}>
        {!isLitersMode && (
          <div className="thr">
            <em>80%</em>
          </div>
        )}

        {data.map((item, index) => {
          if (isLitersMode) {
            // Liters mode: single green column scaled to max 16L
            const heightPct = Math.min((item.dailyLiters / 16) * 100, 100);
            return (
              <div key={item.name || index} className="col">
                <div
                  className="b"
                  style={{
                    background: 'var(--g)',
                    height: animated ? `${heightPct}%` : '0%'
                  }}
                >
                  <span>{String(item.dailyLiters).replace('.', ',')} L</span>
                </div>
              </div>
            );
          }

          // 24h Fill percentage mode: dual pair comparing currentPct and forecastPct
          const currentHeight = Math.min(Math.max(item.currentPct, 0), 100);
          const forecastHeight = Math.min(Math.max(item.forecastPct, 0), 100);
          const forecastColor = getBarColor(item.forecastPct);

          return (
            <div key={item.name || index} className="col">
              <div className="pair">
                {/* Current Fill Bar (grayish ink tone) */}
                <div
                  className="b"
                  style={{
                    background: 'color-mix(in srgb, var(--ink) 16%, var(--card))',
                    height: animated ? `${currentHeight}%` : '0%'
                  }}
                >
                  <span>{item.currentPct}%</span>
                </div>

                {/* 24h Projected Fill Bar (color coded based on threshold) */}
                <div
                  className="b"
                  style={{
                    background: forecastColor,
                    height: animated ? `${forecastHeight}%` : '0%'
                  }}
                >
                  <span>{item.forecastPct}%</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="labs" id="labs">
        {data.map((item, index) => (
          <div key={item.name || index}>{item.name}</div>
        ))}
      </div>

      {!isLitersMode && (
        <div
          className="row sm mut"
          id="leg"
          style={{ justifyContent: 'center', marginTop: '14px', gap: '18px' }}
        >
          <span className="row" style={{ gap: '6px' }}>
            <i
              className="sw"
              style={{ background: 'color-mix(in srgb, var(--ink) 16%, var(--card))' }}
            />
            Hoy
          </span>
          <span className="row" style={{ gap: '6px' }}>
            <i className="sw" style={{ background: 'var(--g)' }} />
            En 24 h
          </span>
        </div>
      )}
    </Card>
  );
}

export default ProjectionChart;
