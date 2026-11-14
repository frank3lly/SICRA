import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Button, CheckIcon } from '../common';
import { updateUser, fetchBusinesses } from '../../services/api';

/**
 * Modal for editing existing user accounts across roles (Admin only).
 *
 * @param {boolean} isOpen - Whether modal is open
 * @param {object} user - User record being edited
 * @param {function} onClose - Close callback
 * @param {function} onSuccess - Callback when user is updated
 */
export function EditUserModal({ isOpen, user, onClose, onSuccess }) {
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'ADMIN',
    business_id: '',
    is_active: true
  });

  const [businesses, setBusinesses] = useState([]);
  const [selectedBusiness, setSelectedBusiness] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    if (user && isOpen) {
      setForm({
        full_name: user.full_name || '',
        email: user.email || '',
        password: '',
        role: user.role || 'ADMIN',
        business_id: user.business_id || '',
        is_active: user.is_active ?? true
      });
      setError(null);
      setSearchTerm('');

      fetchBusinesses({ limit: 50 })
        .then((data) => {
          if (mounted && Array.isArray(data)) {
            setBusinesses(data);
            if (user.business_id) {
              const matched = data.find((b) => b.id === user.business_id);
              if (matched) setSelectedBusiness(matched);
            }
          }
        })
        .catch(() => {});
    }
    return () => {
      mounted = false;
    };
  }, [user, isOpen]);

  // Debounced search for establishments when role is BUSINESS_OWNER
  useEffect(() => {
    let active = true;
    if (form.role !== 'BUSINESS_OWNER' || !searchTerm.trim()) return;

    setIsSearching(true);
    const timer = setTimeout(() => {
      fetchBusinesses({ search: searchTerm, limit: 20 })
        .then((data) => {
          if (active && Array.isArray(data)) {
            setBusinesses(data);
            setIsSearching(false);
          }
        })
        .catch(() => {
          if (active) setIsSearching(false);
        });
    }, 200);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [searchTerm, form.role]);

  const filteredBusinesses = useMemo(() => {
    if (!searchTerm.trim()) return businesses.slice(0, 8);
    const q = searchTerm.toLowerCase();
    return businesses.filter(
      (b) =>
        b.name?.toLowerCase().includes(q) ||
        (b.address && b.address.toLowerCase().includes(q)) ||
        (b.city && b.city.toLowerCase().includes(q))
    ).slice(0, 10);
  }, [businesses, searchTerm]);

  // Handle Escape key
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape' && isOpen && !submitting) {
        onClose();
      }
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, submitting, onClose]);

  if (!isOpen || !user) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!form.full_name.trim()) {
      setError('Por favor ingresa el nombre y apellido del usuario.');
      return;
    }

    if (!form.email.trim() || !form.email.includes('@')) {
      setError('Por favor ingresa un correo electrónico válido.');
      return;
    }

    if (form.role === 'BUSINESS_OWNER' && !form.business_id) {
      setError('Los usuarios con rol Generador Gastronómico deben estar vinculados a un comercio.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        full_name: form.full_name.trim(),
        email: form.email.trim().toLowerCase(),
        role: form.role,
        business_id: form.role === 'BUSINESS_OWNER' ? form.business_id : null,
        is_active: Boolean(form.is_active)
      };

      if (form.password.trim()) {
        if (form.password.trim().length < 8) {
          setError('La nueva contraseña debe tener al menos 8 caracteres.');
          setSubmitting(false);
          return;
        }
        payload.password = form.password.trim();
      }

      const updated = await updateUser(user.id, payload);
      setSubmitting(false);
      if (onSuccess) {
        onSuccess(updated);
      }
      onClose();
    } catch (err) {
      setSubmitting(false);
      setError(err.message || 'Error al actualizar el usuario.');
    }
  };

  return createPortal(
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) {
          onClose();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-user-title"
    >
      <div className="modal-card" style={{ maxWidth: '520px' }}>
        <div style={{ marginBottom: '20px' }}>
          <h2 id="edit-user-title" style={{ margin: '0 0 6px', fontSize: '22px' }}>
            Editar Usuario
          </h2>
          <div className="sm mut" style={{ fontSize: '13px' }}>
            Modifica datos de acceso, permisos y asignación del usuario.
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Nombre Completo */}
          <div className="form-group">
            <label htmlFor="edit-user-name">Nombre y apellido *</label>
            <input
              id="edit-user-name"
              type="text"
              className="form-control"
              required
              placeholder="Ej. Ing. Laura Santana"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            />
          </div>

          {/* Correo y Rol */}
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label htmlFor="edit-user-email">Correo institucional *</label>
              <input
                id="edit-user-email"
                type="email"
                className="form-control"
                required
                placeholder="usuario@sicra.do"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label htmlFor="edit-user-role">Rol en el sistema *</label>
              <select
                id="edit-user-role"
                className="form-control"
                value={form.role}
                onChange={(e) => {
                  const newRole = e.target.value;
                  setForm({
                    ...form,
                    role: newRole,
                    business_id: newRole === 'BUSINESS_OWNER' ? form.business_id : ''
                  });
                }}
              >
                <option value="ADMIN">Administrador (Control total)</option>
                <option value="COLLECTOR">Recolector (Rutas y pesaje)</option>
                <option value="BUSINESS_OWNER">Generador (Comercio / UCO)</option>
              </select>
            </div>
          </div>

          {/* Comercio Vinculado (Solo si es BUSINESS_OWNER) */}
          {form.role === 'BUSINESS_OWNER' && (
            <div
              className="form-group"
              style={{
                background: 'var(--nt, #f8fafc)',
                padding: '12px 14px',
                borderRadius: '8px',
                border: '1px solid var(--border, #e2e8f0)'
              }}
            >
              <label htmlFor="edit-user-biz-search" style={{ marginBottom: '6px' }}>
                Comercio asignado *
              </label>

              {selectedBusiness ? (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    background: 'var(--card, #fff)',
                    borderRadius: '6px',
                    border: '1px solid var(--border, #cbd5e1)'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '13px' }}>{selectedBusiness.name}</div>
                    <div className="sm mut" style={{ fontSize: '11px' }}>
                      {selectedBusiness.address} · {selectedBusiness.city}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedBusiness(null);
                      setForm({ ...form, business_id: '' });
                    }}
                    style={{
                      border: 0,
                      background: 'none',
                      color: 'var(--red, #b91c1c)',
                      fontSize: '12px',
                      cursor: 'pointer',
                      fontWeight: 500
                    }}
                  >
                    Cambiar
                  </button>
                </div>
              ) : (
                <div>
                  <input
                    id="edit-user-biz-search"
                    type="text"
                    className="form-control"
                    placeholder="Buscar comercio por nombre o sector…"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{ marginBottom: '8px' }}
                  />

                  <div
                    style={{
                      maxHeight: '140px',
                      overflowY: 'auto',
                      border: '1px solid var(--border, #e2e8f0)',
                      borderRadius: '6px',
                      background: 'var(--card, #fff)'
                    }}
                  >
                    {filteredBusinesses.map((b) => (
                      <div
                        key={b.id}
                        onClick={() => {
                          setSelectedBusiness(b);
                          setForm({ ...form, business_id: b.id });
                        }}
                        style={{
                          padding: '7px 10px',
                          cursor: 'pointer',
                          fontSize: '12px',
                          borderBottom: '1px solid var(--border, #f1f5f9)',
                          display: 'flex',
                          justifyContent: 'space-between'
                        }}
                      >
                        <span style={{ fontWeight: 500 }}>{b.name}</span>
                        <span className="sm mut">{b.city}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Contraseña Nueva (Opcional) */}
          <div className="form-group">
            <label htmlFor="edit-user-pass">Nueva contraseña (opcional)</label>
            <input
              id="edit-user-pass"
              type="password"
              className="form-control"
              placeholder="Dejar en blanco para conservar la contraseña actual"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </div>

          {/* Estado Activo */}
          <div className="form-group" style={{ marginTop: '8px' }}>
            <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: 500 }}>
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
              />
              <span>Cuenta de usuario activa y con acceso permitido</span>
            </label>
          </div>

          {/* Error Banner */}
          {error && (
            <div
              className="note"
              style={{
                background: 'color-mix(in srgb, var(--red, #b91c1c) 15%, transparent)',
                color: 'var(--red, #b91c1c)',
                border: '1px solid color-mix(in srgb, var(--red, #b91c1c) 30%, transparent)',
                marginBottom: '18px',
                fontSize: '13px'
              }}
            >
              <span>{error}</span>
            </div>
          )}

          {/* Botones de acción */}
          <div className="row sp" style={{ marginTop: '24px' }}>
            <Button
              type="button"
              variant="s"
              disabled={submitting}
              onClick={onClose}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="p"
              disabled={submitting}
            >
              {submitting ? 'Guardando cambios…' : 'Guardar cambios'}
            </Button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}

export default EditUserModal;
