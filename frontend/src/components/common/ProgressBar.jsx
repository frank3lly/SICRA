import React from 'react';

/**
 * Dynamic progress bar matching `.bar`
 * @param {number} value - Fill percentage (0 to 100)
 * @param {string} className - Optional container class
 */
export function ProgressBar({ value = 0, className = '', ...props }) {
  const numericValue = typeof value === 'number' ? value : parseFloat(value) || 0;
  const clampedValue = Math.min(Math.max(numericValue, 0), 100);

  let toneClass = '';
  if (clampedValue >= 95) {
    toneClass = 'c'; // Critical (red)
  } else if (clampedValue >= 80) {
    toneClass = 'w'; // Warning (yellow)
  } // < 80 is default green

  return (
    <div
      className={`bar ${className}`.trim()}
      role="progressbar"
      aria-valuenow={clampedValue}
      aria-valuemin={0}
      aria-valuemax={100}
      {...props}
    >
      <i
        className={toneClass}
        style={{ width: `${clampedValue}%` }}
      />
    </div>
  );
}

export default ProgressBar;
