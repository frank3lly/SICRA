import React from 'react';
import { ShieldIcon, TruckIcon, ShopIcon, LogoutIcon } from '../common/Icon';

/**
 * Global Top Navigation Header
 * Features vector SICRA branding, authenticated role badge, user profile, and session termination.
 *
 * @param {object|null} user - Currently authenticated user
 * @param {function} onBrandClick - Click handler for brand
 * @param {function} onLogout - Logout handler
 */
export function Header({
  user = null,
  onBrandClick,
  onLogout
}) {
  return (
    <header className="sicra-header">
      <div
        className="brand"
        onClick={onBrandClick}
        style={{
          cursor: onBrandClick ? 'pointer' : 'default',
          display: 'flex',
          alignItems: 'center',
          gap: '14px'
        }}
        title="SICRA · Sistema Inteligente de Control y Recolección de Aceite"
      >
        <img
          src="/assets/sicra-navbar-dark.svg"
          alt="SICRA"
          className="brand-logo-full"
          style={{
            height: '38px',
            width: 'auto',
            display: 'block',
            flexShrink: 0
          }}
        />
        <div
          className="brand-subtitle-container"
          style={{
            borderLeft: '1px solid var(--line)',
            paddingLeft: '12px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}
        >
          <div
            className="sm mut"
            style={{
              fontSize: '12px',
              fontWeight: 500,
              lineHeight: 1.25,
              color: 'var(--mut)',
              maxWidth: '300px'
            }}
          >
            Sistema Inteligente de Control y Recolección de Aceite
          </div>
        </div>
      </div>

      {user && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          {/* Active Role Badge */}
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
            {user.role === 'ADMIN' ? (
              <>
                <ShieldIcon style={{ width: '14px', height: '14px', color: 'var(--p)' }} />
                <span>Panel de Administración</span>
              </>
            ) : user.role === 'COLLECTOR' ? (
              <>
                <TruckIcon style={{ width: '14px', height: '14px', color: 'var(--g)' }} />
                <span>Despacho de Recolección</span>
              </>
            ) : (
              <>
                <ShopIcon style={{ width: '14px', height: '14px', color: 'var(--o)' }} />
                <span>Establecimiento Gastronómico</span>
              </>
            )}
          </div>

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
