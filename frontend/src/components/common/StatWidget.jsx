import React from 'react';

/**
 * Metric summary card matching `.card.stat`
 * @param {string|React.ReactNode} label - Metric label
 * @param {string|number} value - Formatted value displayed in Source Serif 4 (30px)
 * @param {React.ReactNode} icon - Optional icon node displayed in .l
 * @param {string} className - Optional custom class name
 */
export function StatWidget({ label, value, icon = null, className = '', ...props }) {
  return (
    <div className={`card stat ${className}`.trim()} {...props}>
      <div className="l">
        {icon}
        <span>{label}</span>
      </div>
      <div className="v">{value}</div>
    </div>
  );
}

export default StatWidget;
