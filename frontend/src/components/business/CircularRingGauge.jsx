import React from 'react';
import { Card, ClockIcon } from '../common';

/**
 * Animated Circular Progress Ring Gauge
 * Displays real-time used cooking oil fill percentage, volume, and recommended collection horizon.
 *
 * @param {number} percentage - Current fill percentage (0-100)
 * @param {number} currentVolume - Current volume in liters
 * @param {number} capacity - Container maximum capacity in liters
 * @param {number|null} hoursRemaining - Hours remaining until collection recommendation
 */
export function CircularRingGauge({
  percentage = 0,
  currentVolume = 0,
  capacity = 50,
  hoursRemaining = null
}) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius; // ~339.292 px
  const clampedPct = Math.max(0, Math.min(100, Number(percentage) || 0));
  const dashLength = (clampedPct / 100) * circumference;

  // Color tone according to threshold
  const strokeColor =
    clampedPct >= 95
      ? 'var(--red)'
      : clampedPct >= 80
      ? '#E0A81E'
      : 'var(--g)';

  // Action horizon text
  const getRecommendationText = () => {
    if (clampedPct >= 95) {
      return (
        <span>
          Recolección prioritaria recomendada: <b>Atención inmediata</b>
        </span>
      );
    }
    if (clampedPct >= 80) {
      if (hoursRemaining !== null && hoursRemaining !== undefined && hoursRemaining > 0) {
        return (
          <span>
            Recolección recomendada en unas <b>{Math.round(hoursRemaining)} horas</b>
          </span>
        );
      }
      return (
        <span>
          Recolección recomendada: <b>Capacidad superó el 80%</b>
        </span>
      );
    }
    if (hoursRemaining !== null && hoursRemaining !== undefined && hoursRemaining > 0) {
      return (
        <span>
          Llegada al 80% estimada en unas <b>{Math.round(hoursRemaining)} horas</b>
        </span>
      );
    }
    return (
      <span>
        Nivel óptimo de almacenamiento · <b>Capacidad disponible</b>
      </span>
    );
  };

  const formattedVolume = String(Number(currentVolume).toFixed(1)).replace('.', ',');
  const formattedCapacity = String(Number(capacity).toFixed(0));

  return (
    <Card style={{ padding: '30px' }}>
      <div className="ring">
        <svg viewBox="0 0 130 130" width="190" height="190" aria-label={`Nivel del contenedor: ${Math.round(clampedPct)}%`}>
          {/* Neutral track circle */}
          <circle
            cx="65"
            cy="65"
            r={radius}
            fill="none"
            stroke="var(--nt)"
            strokeWidth="11"
          />
          {/* Active progress arc */}
          <circle
            cx="65"
            cy="65"
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth="11"
            strokeLinecap="round"
            strokeDasharray={`${dashLength.toFixed(1)} ${circumference.toFixed(1)}`}
            transform="rotate(-90 65 65)"
            style={{
              transition: 'stroke-dasharray 0.8s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.4s ease'
            }}
          />
        </svg>
        <b>
          {Math.round(clampedPct)}%
          <small>
            {formattedVolume} de {formattedCapacity} L
          </small>
        </b>
      </div>

      <div className="row" style={{ justifyContent: 'center', marginTop: '20px' }}>
        <ClockIcon
          style={{
            color: clampedPct >= 95 ? 'var(--red)' : clampedPct >= 80 ? 'var(--o)' : 'var(--g)',
            flexShrink: 0
          }}
        />
        {getRecommendationText()}
      </div>
    </Card>
  );
}

export default CircularRingGauge;
