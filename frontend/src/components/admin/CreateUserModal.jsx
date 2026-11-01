import React, { useState, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { Button, CheckIcon, SparkIcon } from '../common';
import { createUser, fetchBusinesses } from '../../services/api';

/**
 * Modal for creating and provisioning system users across roles.
 *
 * @param {boolean} isOpen - Whether modal is open
 * @param {function} onClose - Close callback
 * @param {function} onSuccess - Callback when user is created
 */
export function CreateUserModal({ isOpen, onClose, onSuccess }) {
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'ADMIN',
    business_id: ''
  });

  const [businesses, setBusinesses] = useState([]);
  const [selectedBusiness, setSelectedBusiness] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [createdSuccess, setCreatedSuccess] = useState(null);

  // Reset form and load businesses when modal opens
  useEffect(() => {
    let mounted = true;
    if (isOpen) {
      setError(null);
      setCreatedSuccess(null);
      setSelectedBusiness(null);
      setSearchTerm('');
      setForm({
        full_name: '',
        email: '',
        password: '',
        role: 'ADMIN',
        business_id: ''
      });

      fetchBusinesses({ limit: 50 })
        .then((data) => {
          if (mounted && Array.isArray(data)) {
            setBusinesses(data);
          }
        })
        .catch(() => {
          // Non-critical if businesses fail initially
        });
    }
    return () => {
      mounted = false;
    };
  }, [isOpen]);

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

  // Filter businesses locally as well
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
        handleClose();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, submitting]);

  // Lock body scroll while modal is active
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleClose = () => {
    setError(null);
    setCreatedSuccess(null);
    setSelectedBusiness(null);
    setSearchTerm('');
    onClose();
  };

  const generatePassword = () => {
    const chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let randomPart = '';
    for (let i = 0; i < 6; i++) {
      randomPart += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    const pin = Math.floor(Math.random() * 900 + 100);
    const generated = `Sicra${randomPart}!${pin}`;
    setForm((prev) => ({ ...prev, password: generated }));
  };

  const handleSelectBusiness = (b) => {
    setSelectedBusiness(b);
    setForm((prev) => ({ ...prev, business_id: b.id }));
    setSearchTerm('');
    setError(null);
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setError(null);

    if (form.role === 'BUSINESS_OWNER' && !form.business_id) {
      setError('Por favor busca y selecciona el comercio asignado para este usuario.');
      return;
    }

    if (!form.password || form.password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres.');
      return;
    }

    try {
      setSubmitting(true);
      const payload = {
        full_name: form.full_name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
        role: form.role,
        business_id: form.role === 'BUSINESS_OWNER' ? form.business_id : null
      };

      const result = await createUser(payload);
      setSubmitting(false);
      setCreatedSuccess(result);

      if (onSuccess) {
        onSuccess(result);
      }
      setTimeout(() => {
        handleClose();
      }, 1200);
    } catch (err) {
      setSubmitting(false);
      setError(err.message || 'Error al crear el usuario.');
    }
  };

  return createPortal(
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) {
          handleClose();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="user-modal-title"
    >
      <div className="modal-card" style={{ maxWidth: '500px' }}>
        <div style={{ marginBottom: '20px' }}>
          <h2 id="user-modal-title" style={{ margin: '0 0 6px', fontSize: '22px' }}>
            Crear nuevo usuario
          </h2>
          <div className="sm mut" style={{ fontSize: '13px' }}>
            Asigna permisos y roles de acceso para administradores, recolectores o comercios.
          </div>
        </div>

        {createdSuccess ? (
          <div
            style={{
              padding: '24px 16px',
              textAlign: 'center',
              background: 'color-mix(in srgb, var(--g) 12%, var(--card))',
              border: '1px solid var(--g)',
              borderRadius: '10px',
              animation: 'fadeIn 0.2s ease'
            }}
          >
            <div style={{ color: 'var(--g)', marginBottom: '8px' }}>
              <CheckIcon />
            </div>
            <div style={{ fontWeight: 600, fontSize: '16px', color: 'var(--ink)' }}>
              Usuario creado exitosamente
            </div>
            <div className="sm mut" style={{ marginTop: '4px', fontSize: '13px' }}>
              {createdSuccess.full_name} ({createdSuccess.email})
            </div>
          </div>
        ) : (
          <form onSubmit={handleCreateUser}>
            {/* 1. Nombre completo */}
            <div className="form-group">
              <label htmlFor="user-fullname">Nombre completo *</label>
              <input
                id="user-fullname"
                type="text"
                className="form-control"
                required
                placeholder="Ej. Carlos Manuel Zorrilla"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                autoFocus
              />
            </div>

            {/* 2. Correo electrónico */}
            <div className="form-group">
              <label htmlFor="user-email">Correo electrónico (Login) *</label>
              <input
                id="user-email"
                type="email"
                className="form-control"
                required
                placeholder="correo@ejemplo.do"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>

            {/* 3. Contraseña temporal con generador */}
            <div className="form-group">
              <div className="row sp" style={{ marginBottom: '6px' }}>
                <label htmlFor="user-password" style={{ margin: 0 }}>
                  Contraseña temporal *
                </label>
                <button
                  type="button"
                  className="chip"
                  onClick={generatePassword}
                  style={{
                    cursor: 'pointer',
                    background: 'var(--nt)',
                    border: '1px solid var(--line)',
                    fontWeight: 500,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px'
                  }}
                >
                  <SparkIcon style={{ width: '13px', height: '13px', color: 'var(--g)' }} />
                  <span>Generar segura</span>
                </button>
              </div>
              <input
                id="user-password"
                type="text"
                className="form-control"
                required
                minLength={8}
                placeholder="Mínimo 8 caracteres"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </div>

            {/* 4. Rol de acceso */}
            <div className="form-group">
              <label htmlFor="user-role">Rol de acceso *</label>
              <select
                id="user-role"
                className="form-control"
                value={form.role}
                onChange={(e) => {
                  const newRole = e.target.value;
                  setForm({
                    ...form,
                    role: newRole,
                    business_id: newRole === 'BUSINESS_OWNER' ? form.business_id : ''
                  });
                  if (newRole !== 'BUSINESS_OWNER') {
                    setSelectedBusiness(null);
                  }
                }}
              >
                <option value="ADMIN">Administrador (Control total del sistema)</option>
                <option value="COLLECTOR">Recolector (Chofer / Logística de recolección)</option>
                <option value="BUSINESS_OWNER">Encargado de Negocio (Vista de su contenedor)</option>
              </select>
            </div>

            {/* 5. Comercio Asociado (Condicional: Sólo si el rol es BUSINESS_OWNER) */}
            {form.role === 'BUSINESS_OWNER' && (
              <div className="form-group" style={{ animation: 'fadeIn 0.2s ease' }}>
                <label>Comercio asignado *</label>

                {selectedBusiness ? (
                  <div
                    style={{
                      background: 'var(--nt)',
                      border: '1px solid var(--line)',
                      borderRadius: '8px',
                      padding: '10px 14px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--ink)' }}>
                        {selectedBusiness.name}
                      </div>
                      <div className="sm mut" style={{ fontSize: '11px', marginTop: '2px' }}>
                        {selectedBusiness.address} · {selectedBusiness.city}
                      </div>
                    </div>
                    <button
                      type="button"
                      className="btn sm"
                      onClick={() => {
                        setSelectedBusiness(null);
                        setForm((prev) => ({ ...prev, business_id: '' }));
                        setSearchTerm('');
                      }}
                      style={{ padding: '4px 10px', fontSize: '12px' }}
                    >
                      Cambiar
                    </button>
                  </div>
                ) : (
                  <div>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Buscar comercio por nombre o dirección..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />

                    <div
                      style={{
                        marginTop: '6px',
                        maxHeight: '160px',
                        overflowY: 'auto',
                        background: 'var(--card)',
                        border: '1px solid var(--line)',
                        borderRadius: '8px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.08)'
                      }}
                    >
                      {isSearching ? (
                        <div className="sm mut" style={{ padding: '10px 14px', textAlign: 'center' }}>
                          Buscando comercios...
                        </div>
                      ) : filteredBusinesses.length === 0 ? (
                        <div className="sm mut" style={{ padding: '10px 14px', textAlign: 'center' }}>
                          {searchTerm.trim()
                            ? `No se encontraron comercios que coincidan con "${searchTerm}".`
                            : 'Escribe para buscar entre los comercios registrados.'}
                        </div>
                      ) : (
                        filteredBusinesses.map((b) => (
                          <div
                            key={b.id}
                            onClick={() => handleSelectBusiness(b)}
                            style={{
                              padding: '8px 12px',
                              cursor: 'pointer',
                              borderBottom: '1px solid var(--line)',
                              transition: 'background 0.15s ease'
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--nt)')}
                            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                          >
                            <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--ink)' }}>
                              {b.name}
                            </div>
                            <div className="sm mut" style={{ fontSize: '11px', marginTop: '1px' }}>
                              {b.address} · {b.city}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
                <span className="sm mut" style={{ display: 'block', marginTop: '6px', fontSize: '12px' }}>
                  Este usuario solo podrá ver los datos y alertas de este comercio.
                </span>
              </div>
            )}

            {/* Feedback de error */}
            {error && (
              <div
                className="note"
                style={{
                  background: 'color-mix(in srgb, var(--red) 15%, var(--card))',
                  color: 'var(--red)',
                  marginTop: '14px',
                  fontSize: '13px',
                  borderRadius: '8px'
                }}
              >
                {error}
              </div>
            )}

            {/* Acciones */}
            <div className="row sp" style={{ marginTop: '24px' }}>
              <button
                type="button"
                className="btn"
                onClick={handleClose}
                disabled={submitting}
              >
                Cancelar
              </button>
              <button type="submit" className="btn p" disabled={submitting}>
                {submitting ? 'Creando usuario...' : 'Crear usuario'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>,
    document.body
  );
}

export default CreateUserModal;
