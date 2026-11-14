import React, { useState } from 'react';
import { Card, Chip } from '../common';
import { getStoredUser } from '../../services/api';

const PAGE_SIZE = 10;

const ROLE_LABELS = {
  ADMIN: 'Administrador',
  COLLECTOR: 'Recolector',
  BUSINESS_OWNER: 'Generador'
};

const ROLE_VARIANTS = {
  ADMIN: 'c',
  COLLECTOR: 'w',
  BUSINESS_OWNER: ''
};

/**
 * Administrative Users Management Table
 *
 * @param {Array<object>} users - List of registered users
 * @param {function} onEdit - Edit callback
 * @param {function} onDelete - Delete callback
 */
export function UsersTable({
  users = [],
  onEdit,
  onDelete,
  className = '',
  ...props
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const currentUser = getStoredUser();

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
    setCurrentPage(1);
  };

  const handleRoleChange = (e) => {
    setRoleFilter(e.target.value);
    setCurrentPage(1);
  };

  const filtered = users.filter((u) => {
    if (roleFilter && u.role !== roleFilter) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (u.full_name || '').toLowerCase().includes(q) ||
      (u.email || '').toLowerCase().includes(q)
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
          <h2>Gestión de Usuarios</h2>
          <span className="sm mut">
            {users.length} cuentas registradas en el sistema
          </span>
        </div>

        <div className="row" style={{ gap: '10px' }}>
          {/* Role Filter */}
          <select
            className="form-control"
            style={{ width: 'auto', padding: '6px 12px', fontSize: '13px' }}
            value={roleFilter}
            onChange={handleRoleChange}
          >
            <option value="">Todos los roles</option>
            <option value="ADMIN">Administradores</option>
            <option value="COLLECTOR">Recolectores</option>
            <option value="BUSINESS_OWNER">Generadores</option>
          </select>

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
              placeholder="Buscar por nombre o correo…"
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
      </div>

      {users.length === 0 ? (
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
          No hay usuarios registrados en el sistema.
        </div>
      ) : (
        <div className="scroll">
          <table>
            <thead>
              <tr>
                <th style={{ minWidth: '180px' }}>Usuario</th>
                <th style={{ minWidth: '200px' }}>Correo Electrónico</th>
                <th style={{ minWidth: '120px' }}>Rol</th>
                <th style={{ minWidth: '160px' }}>Asignación</th>
                <th style={{ width: '90px', textAlign: 'center' }}>Estado</th>
                <th style={{ width: '130px', textAlign: 'right' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {paginated.length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '36px', color: 'var(--mut)' }}>
                    No se encontraron usuarios que coincidan con la búsqueda.
                  </td>
                </tr>
              ) : (
                paginated.map((user) => {
                  const roleLabel = ROLE_LABELS[user.role] || user.role;
                  const roleVariant = ROLE_VARIANTS[user.role] || '';
                  const isActive = user.is_active ?? true;
                  const isSelf = currentUser && (currentUser.id === user.id || currentUser.email === user.email);

                  return (
                    <tr key={user.id}>
                      <td className="business-name-cell">
                        <div style={{ fontWeight: 600 }}>{user.full_name}</div>
                        {isSelf && (
                          <div className="sm mut" style={{ fontSize: '11px', color: 'var(--g)' }}>
                            (Tu cuenta actual)
                          </div>
                        )}
                      </td>
                      <td style={{ fontSize: '13px', fontVariantNumeric: 'tabular-nums' }}>
                        {user.email}
                      </td>
                      <td>
                        <Chip variant={roleVariant}>{roleLabel}</Chip>
                      </td>
                      <td style={{ fontSize: '12px' }}>
                        {user.business_name || (user.business_id ? `ID: ${user.business_id.slice(0, 8)}…` : '—')}
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
                            onClick={() => onEdit && onEdit(user)}
                          >
                            Editar
                          </button>
                          <button
                            type="button"
                            className="pagination-btn"
                            disabled={isSelf}
                            title={isSelf ? 'No puedes eliminar tu propia cuenta' : 'Eliminar usuario'}
                            style={{
                              padding: '4px 10px',
                              fontSize: '12px',
                              color: isSelf ? 'var(--mut)' : 'var(--red, #b91c1c)',
                              borderColor: isSelf
                                ? 'var(--border)'
                                : 'color-mix(in srgb, var(--red, #b91c1c) 30%, transparent)'
                            }}
                            onClick={() => !isSelf && onDelete && onDelete(user)}
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
            <b>{startIndex + 1}–{endIndex}</b> de <b>{totalItems}</b> usuarios
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

export default UsersTable;
