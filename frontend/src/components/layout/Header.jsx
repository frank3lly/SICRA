import React from 'react';
import { ShieldIcon, TruckIcon, ShopIcon, LogoutIcon } from '../common/Icon';

/**
 * Global Top Navigation Header
 * Features vector SICRA branding from official design assets,
 * role-gated navigation, user profile display, and secure logout.
 *
 * @param {object|null} user - Currently authenticated user
 * @param {string} role - Active view role ('admin' | 'col' | 'biz')
 * @param {function} setRole - Role setter function
 * @param {function} onBrandClick - Click handler for brand
 * @param {function} onLogout - Logout handler
 */
export function Header({
  user = null,
  role = 'admin',
  setRole,
  onBrandClick,
  onLogout
}) {
  const isAdmin = user?.role === 'ADMIN';

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

      {user && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          {isAdmin ? (
            <nav className="seg" aria-label="Navegación por rol administrativo">
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
          ) : (
            <div
              className="chip"
              style={{
                background: 'var(--nt)',
                color: 'var(--ink)',
                border: '1px solid var(--line)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600
              }}
            >
              {user.role === 'COLLECTOR' ? (
                <>
                  <TruckIcon style={{ width: '14px', height: '14px', color: 'var(--g)' }} />
                  <span>Ruta de Recolección</span>
                </>
              ) : (
                <>
                  <ShopIcon style={{ width: '14px', height: '14px', color: 'var(--o)' }} />
                  <span>Establecimiento Gastronómico</span>
                </>
              )}
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="header-user-text">
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink)' }}>
                {user.full_name}
              </div>
              <div className="sm mut" style={{ fontSize: '11px', color: 'var(--mut)' }}>
                {user.email}
              </div>
            </div>

            <button
              type="button"
              className="btn"
              onClick={onLogout}
              title="Cerrar sesión"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 12px',
                fontSize: '12px',
                fontWeight: 500,
                background: 'var(--card)',
                border: '1px solid var(--line)',
                borderRadius: '8px',
                color: 'var(--ink)'
              }}
            >
              <LogoutIcon style={{ width: '14px', height: '14px' }} />
              <span>Cerrar sesión</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
}

export default Header;
