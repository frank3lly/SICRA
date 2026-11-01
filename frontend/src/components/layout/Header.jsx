import React, { useState } from 'react';
import { ShieldIcon, TruckIcon, ShopIcon } from '../common/Icon';

/**
 * Global Top Navigation Header
 * @param {string} role - Current role ('admin' | 'col' | 'biz')
 * @param {function} setRole - Role setter function
 */
export function Header({ role = 'admin', setRole }) {
  const [imgError, setImgError] = useState(false);

  return (
    <header>
      <div className="brand">
        {!imgError ? (
          <img
            src="/assets/sicra_logo.jpeg"
            alt="SICRA Logo"
            className="brand-logo-img"
            onError={() => setImgError(true)}
          />
        ) : (
          <svg width="40" height="40" viewBox="0 0 48 48" aria-hidden="true">
            <path d="M8 24a16 16 0 0 1 28-10.500" fill="none" stroke="#5D8054" strokeWidth="3.500" strokeLinecap="round" />
            <path d="M40 24a16 16 0 0 1-28 10.500" fill="none" stroke="#5D8054" strokeWidth="3.500" strokeLinecap="round" />
            <path d="M24 10s8 8.500 8 14a8 8 0 0 1-16 0c0-5.500 8-14 8-14z" fill="#998937" />
            <circle cx="24" cy="27" r="2" fill="#F2F2F2" />
          </svg>
        )}
        <div>
          <b>SICRA</b>
          <div className="sm mut" style={{ lineHeight: 1.2 }}>Control y recolección de aceite</div>
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
