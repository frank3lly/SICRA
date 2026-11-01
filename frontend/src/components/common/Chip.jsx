import React from 'react';

/**
 * Status badge pill matching `.chip`, `.chip.w`, `.chip.c`
 * @param {'w' | 'c' | ''} variant - "w" (warning yellow), "c" (critical red), or default (primary green)
 * @param {string} className - Optional custom class name
 * @param {React.ReactNode} children - Chip content
 */
export function Chip({ variant = '', children, className = '', ...props }) {
  const variantClass = variant ? `chip ${variant}` : 'chip';
  return (
    <span className={`${variantClass} ${className}`.trim()} {...props}>
      {children}
    </span>
  );
}

export default Chip;
