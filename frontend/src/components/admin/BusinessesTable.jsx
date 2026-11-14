import React, { useState } from 'react';
import { Card, Chip } from '../common';

const PAGE_SIZE = 10;

const TYPE_LABELS = {
  PICA_POLLO: 'Pica Pollo',
  FRITURA: 'Fritura',
  CAFETERIA: 'Cafetería',
  RESTAURANTE: 'Restaurante'
};

/**
 * Administrative Businesses Management Table
 *
 * @param {Array<object>} businesses - List of businesses
 * @param {function} onEdit - Edit callback
 * @param {function} onDelete - Delete callback
 */
export function BusinessesTable({
  businesses = [],
  onEdit,
  onDelete,
  className = '',
  ...props
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
    setCurrentPage(1);
  };

  const filtered = businesses.filter((b) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (b.name || '').toLowerCase().includes(q) ||
      (b.address || '').toLowerCase().includes(q) ||
      (b.city || '').toLowerCase().includes(q) ||
      (b.phone || '').toLowerCase().includes(q)
    );
  });

  const totalItems = filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * PAGE_SIZE;
  const endIndex = Math.min(startIndex + PAGE_SIZE, totalItems);
  const paginated = filtered.slice(startIndex, endIndex);

  return (
    <Card className={`fleet-table-card ${className}`.trim()} {...props}>
      <div className="row sp" style={{ marginBottom: '16px', gap: '16px' }}>
        <div>
          <h2>Gestión de Comercios</h2>
          <span className="sm mut">
            {businesses.length} establecimientos gastronómicos registrados
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
            placeholder="Buscar por nombre o sector…"
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
                display: 'inline-flex',
                alignItems: 'center',
                padding: '2px'
              }}
              aria-label="Limpiar filtro"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {businesses.length === 0 ? (
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
          No hay comercios registrados en el sistema.
        </div>
      ) : (
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th style={{ minWidth: '170px' }}>Comercio</th>
                <th style={{ minWidth: '110px' }}>Tipo</th>
                <th style={{ minWidth: '120px' }}>Operación</th>
                <th style={{ minWidth: '180px' }}>Ubicación</th>
                <th style={{ width: '90px', textAlign: 'center' }}>Estado</th>
                <th style={{ width: '130px', textAlign: 'right' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {paginated.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '36px', color: 'var(--mut)' }}>
                    No se encontraron comercios que coincidan con "{searchQuery}".
                  </td>
                </tr>
              ) : (
                paginated.map((biz) => {
                  const typeLabel = TYPE_LABELS[biz.business_type] || biz.business_type || 'Comercio';
                  const isActive = biz.is_active ?? true;

                  return (
                    <tr key={biz.id}>
                      <td className="business-name-cell">
                        <div style={{ fontWeight: 600 }}>{biz.name}</div>
                        {biz.phone && (
                          <div className="sm mut" style={{ fontSize: '11px', marginTop: '2px' }}>
                            {biz.phone}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className="chip" style={{ fontSize: '11px' }}>{typeLabel}</span>
                      </td>
                      <td style={{ fontSize: '12px' }}>
                        <div>{biz.num_fryers ?? 1} {biz.num_fryers === 1 ? 'freidora' : 'freidoras'}</div>
                        <div className="sm mut" style={{ fontSize: '11px' }}>
                          ~{biz.avg_daily_customers ?? 50} clientes/día
                        </div>
                      </td>
                      <td style={{ fontSize: '12px' }}>
                        <div>{biz.address || '—'}</div>
                        <div className="sm mut" style={{ fontSize: '11px' }}>
                          {biz.city || 'San Pedro de Macorís'}
                        </div>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <Chip variant={isActive ? '' : 'c'}>
                          {isActive ? 'Activo' : 'Inactivo'}
                        </Chip>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="row" style={{ gap: '6px', justifyContent: 'flex-end' }}>
                          <button
                            type="button"
                            className="pagination-btn"
                            style={{ padding: '4px 10px', fontSize: '12px' }}
                            onClick={() => onEdit && onEdit(biz)}
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            className="pagination-btn"
                            style={{
                              padding: '4px 10px',
                              fontSize: '12px',
                              color: 'var(--red, #b91c1c)',
                              borderColor: 'color-mix(in srgb, var(--red, #b91c1c) 30%, transparent)'
                            }}
                            onClick={() => onDelete && onDelete(biz)}
                          >
                            Eliminar
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Bar */}
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

export default BusinessesTable;
