import React from 'react';
import { ShieldIcon, TruckIcon, ShopIcon } from '../common/Icon';

/**
 * Global Top Navigation Header
 * Features vector SICRA branding from official design assets and role switcher
 * @param {string} role - Current role ('admin' | 'col' | 'biz')
 * @param {function} setRole - Role setter function
 * @param {function} onBrandClick - Optional click handler for returning to dashboard root
 */
export function Header({ role = 'admin', setRole, onBrandClick }) {
  return (
    <header className="sicra-header">
      <div
        className="brand"
        onClick={onBrandClick}
        style={{ cursor: onBrandClick ? 'pointer' : 'default' }}
        title="SICRA · Plataforma Oficial"
      >
        <img
          src="/assets/sicra-isotype.svg"
          alt="SICRA Isotipo"
          className="brand-logo-svg"
          style={{
            width: '40px',
            height: '40px',
            display: 'block',
            flexShrink: 0
          }}
        />
        <div>
          <b>SICRA</b>
          <div className="sm mut" style={{ lineHeight: 1.2 }}>
            Control y recolección de aceite
          </div>
        </div>
      </div>

      <nav className="seg" aria-label="Vista previa por rol">
        <button
          type="button"
          aria-pressed={role === 'admin'}
          onClick={() => setRole && setRole('admin')}
        >
          <ShieldIcon /> Administrador
        </button>
        <button
          type="button"
          aria-pressed={role === 'col'}
          onClick={() => setRole && setRole('col')}
        >
          <TruckIcon /> Recolector
        </button>
        <button
          type="button"
          aria-pressed={role === 'biz'}
          onClick={() => setRole && setRole('biz')}
        >
          <ShopIcon /> Negocio
        </button>
      </nav>
    </header>
  );
}

export default Header;
