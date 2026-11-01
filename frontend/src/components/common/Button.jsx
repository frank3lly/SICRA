import React from 'react';

/**
 * Reusable Button component matching `.btn`, `.btn.p`, `.btn.n`, `.btn.sm`
 * @param {'p' | 'n' | ''} variant - "p" (primary eco green), "n" (Dominican navy), or default (card white)
 * @param {React.ReactNode} icon - Optional icon node or component
 * @param {boolean} disabled - Disabled state
 * @param {function} onClick - Click handler
 * @param {string} className - Additional CSS classes
 * @param {string} size - Optional size ("sm" for compact)
 * @param {React.ReactNode} children - Button text / children
 */
export function Button({
  variant = '',
  icon = null,
  disabled = false,
  onClick,
  children,
  className = '',
  size = '',
  type = 'button',
  ...props
}) {
  const variantClass = variant ? `btn ${variant}` : 'btn';
  const sizeClass = size ? `btn ${size}` : '';
  const combinedClasses = [
    variantClass,
    sizeClass,
    className
  ].filter(Boolean).join(' ');

  return (
    <button
      type={type}
      className={combinedClasses}
      disabled={disabled}
      onClick={onClick}
      {...props}
    >
      {icon}
      {children && (typeof children === 'string' ? <span>{children}</span> : children)}
    </button>
  );
}

export default Button;
