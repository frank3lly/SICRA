import React from 'react';

/**
 * Standard container card matching `.card`
 * @param {string} className - Additional CSS classes
 * @param {React.ReactNode} children - Card content
 */
export function Card({ children, className = '', ...props }) {
  return (
    <div className={`card ${className}`.trim()} {...props}>
      {children}
    </div>
  );
}

export default Card;
