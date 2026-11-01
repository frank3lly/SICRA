import React, { useState } from 'react';
import { Card, ProgressBar, Chip } from '../common';

const PAGE_SIZE = 11;

/**
 * Fleet Containers Table with Searchbar and 11-Item Pagination
 * @param {Array<object>} containers - List of container records
 */
export function FleetTable({ containers = [], className = '', ...props }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
    setCurrentPage(1);
  };

  const filtered = containers.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (c.business_name || '').toLowerCase().includes(q);
  });

  const totalItems = filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * PAGE_SIZE;
  const endIndex = Math.min(startIndex + PAGE_SIZE, totalItems);
  const paginatedContainers = filtered.slice(startIndex, endIndex);

  return (
    <Card className={`fleet-table-card ${className}`.trim()} {...props}>
      <div className="row sp" style={{ marginBottom: '16px', gap: '16px' }}>
        <div>
          <h2>Contenedores en Monitoreo</h2>
          <span className="sm mut">
            {containers.length} comercios registrados en la flota
          </span>
        </div>

        {/* Searchbar */}
        <div className="search-box">
          <svg
            className="i"
            viewBox="0 0 24 24"
            style={{ width: '16px', height: '16px', color: 'var(--mut)' }}
          >
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" fill="none" />
            <line x1="16" y1="16" x2="21" y2="21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            type="text"
            className="search-input"
            placeholder="Buscar comercio…"
            value={searchQuery}
            onChange={handleSearchChange}
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setCurrentPage(1);
              }}
              style={{
                border: 0,
                background: 'none',
                cursor: 'pointer',
                color: 'var(--mut)',
                fontSize: '13px'
              }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {containers.length === 0 ? (
        <div
          className="note"
          style={{
            background: 'var(--nt)',
            color: 'var(--mut)',
            textAlign: 'center',
            justifyContent: 'center',
            padding: '24px'
          }}
        >
          No hay contenedores registrados en la flota.
        </div>
      ) : (
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th style={{ minWidth: '180px' }}>Comercio</th>
                <th style={{ minWidth: '150px' }}>Nivel de Llenado</th>
                <th style={{ width: '80px', textAlign: 'center' }}>Batería IoT</th>
                <th style={{ width: '110px', textAlign: 'right' }}>Estado</th>
              </tr>
            </thead>
            <tbody>
              {paginatedContainers.length === 0 ? (
                <tr>
                  <td colSpan="4" style={{ textAlign: 'center', padding: '36px', color: 'var(--mut)' }}>
                    No se encontraron comercios que coincidan con "{searchQuery}".
                  </td>
                </tr>
              ) : (
                paginatedContainers.map((container) => {
                  const fillPct = container.current_fill_percentage ?? 0;
                  const batteryPct = container.battery_percentage ?? 85;

                  let statusLabel = container.status_label;
                  let statusVariant = container.status_variant;

                  if (!statusLabel) {
                    if (batteryPct < 20) {
                      statusLabel = 'Batería baja';
                      statusVariant = 'w';
                    } else if (fillPct >= 95) {
                      statusLabel = 'Crítico';
                      statusVariant = 'c';
                    } else if (fillPct >= 80) {
                      statusLabel = 'Casi lleno';
                      statusVariant = 'w';
                    } else {
                      statusLabel = 'Normal';
                      statusVariant = '';
                    }
                  }

                  return (
                    <tr key={container.id || container.business_name}>
                      <td className="business-name-cell">
                        {container.business_name}
                      </td>
                      <td>
                        <div className="row" style={{ flexWrap: 'nowrap', gap: '8px' }}>
                          <ProgressBar value={fillPct} />
                          <span style={{ minWidth: '34px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                            {fillPct}%
                          </span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'center', fontVariantNumeric: 'tabular-nums' }}>
                        {batteryPct}%
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <Chip variant={statusVariant}>{statusLabel}</Chip>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Bar (Max 11 per page) */}
      {totalItems > 0 && (
        <div className="pagination-bar">
          <span className="sm mut">
            Página <b>{safeCurrentPage}</b> de <b>{totalPages}</b> · Mostrando{' '}
            <b>{startIndex + 1}–{endIndex}</b> de <b>{totalItems}</b> comercios
          </span>

          <div className="row" style={{ gap: '8px' }}>
            <button
              type="button"
              className="pagination-btn"
              disabled={safeCurrentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            >
              ← Anterior
            </button>
            <button
              type="button"
              className="pagination-btn"
              disabled={safeCurrentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            >
              Siguiente →
            </button>
          </div>
        </div>
      )}
    </Card>
  );
}

export default FleetTable;
