import React from 'react';

/**
 * Segmented toggle control matching `.seg`
 * @param {Array<{value: string, label: React.ReactNode, icon?: React.ReactNode}>} options - Options list
 * @param {string} value - Currently active value
 * @param {function} onChange - Value change handler
 * @param {string} ariaLabel - Accessible name for navigation/group
 * @param {'nav' | 'div'} as - Element tag
 * @param {string} className - Additional CSS classes
 */
export function SegmentedControl({
  options = [],
  value,
  onChange,
  ariaLabel = 'Opciones',
  as: Component = 'div',
  className = '',
  children,
  ...props
}) {
  return (
    <Component
      className={`seg ${className}`.trim()}
      aria-label={ariaLabel}
      role={Component === 'nav' ? 'navigation' : 'group'}
      {...props}
    >
      {options.length > 0
        ? options.map((opt) => {
            const isSelected = opt.value === value;
            return (
              <button
                key={opt.value}
                type="button"
                aria-pressed={isSelected}
                onClick={() => onChange && onChange(opt.value)}
              >
                {opt.icon}
                <span>{opt.label}</span>
              </button>
            );
          })
        : children}
    </Component>
  );
}

export default SegmentedControl;
