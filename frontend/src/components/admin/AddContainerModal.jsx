import React, { useState, useEffect, useMemo } from 'react';
import { Button, CheckIcon } from '../common';
import { fetchBusinesses, createContainer } from '../../services/api';

/**
 * Modal for Provisioning Smart Containers and Generating ESP32 Hardware Tokens
 * Features a high-capacity searchbar for finding businesses among 1k+ establishments.
 *
 * @param {boolean} isOpen - Whether modal is open
 * @param {function} onClose - Close callback
 * @param {function} onSuccess - Callback when container is created
 */
export function AddContainerModal({ isOpen, onClose, onSuccess }) {
  const [step, setStep] = useState(1); // 1: Provisioning Form, 2: ESP32 Flashing Card
  const [businesses, setBusinesses] = useState([]);
  const [selectedBusiness, setSelectedBusiness] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [form, setForm] = useState({
    business_id: '',
    capacity_liters: 50,
    tare_weight_kg: 3.8,
    oil_density_kg_l: 0.92
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [createdContainer, setCreatedContainer] = useState(null);
  const [copiedField, setCopiedField] = useState(null);

  // Fetch initial businesses when modal opens
  useEffect(() => {
    let mounted = true;
    if (isOpen) {
      setStep(1);
      setError(null);
      setCopiedField(null);
      setSelectedBusiness(null);
      setSearchTerm('');
      setForm({
        business_id: '',
        capacity_liters: 50,
        tare_weight_kg: 3.8,
        oil_density_kg_l: 0.92
      });

      fetchBusinesses({ limit: 50 })
        .then((data) => {
          if (mounted && Array.isArray(data)) {
            setBusinesses(data);
          }
        })
        .catch(() => {
          if (mounted) setError('No se pudieron cargar los comercios registrados.');
        });
    }

    return () => {
      mounted = false;
    };
  }, [isOpen]);

  // Live search query to backend when user types (debounced)
  useEffect(() => {
    let active = true;
    if (!searchTerm.trim()) return;

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
  }, [searchTerm]);

  // Filter businesses locally as well
  const filteredBusinesses = useMemo(() => {
    if (!searchTerm.trim()) return businesses.slice(0, 8);
    const q = searchTerm.toLowerCase();
    return businesses.filter(
      (b) =>
        b.name.toLowerCase().includes(q) ||
        (b.address && b.address.toLowerCase().includes(q)) ||
        (b.city && b.city.toLowerCase().includes(q))
    ).slice(0, 10);
  }, [businesses, searchTerm]);

  // Handle escape key
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape' && isOpen) {
        handleClose();
      }
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  if (!isOpen) return null;

  const handleClose = () => {
    if (loading) return;
    setStep(1);
    setError(null);
    setCopiedField(null);
    setSelectedBusiness(null);
    setSearchTerm('');
    onClose();
  };

  const handleSelectBusiness = (b) => {
    setSelectedBusiness(b);
    setForm((prev) => ({ ...prev, business_id: b.id }));
    setSearchTerm('');
    setError(null);
  };

  const copyToClipboard = async (text, fieldName) => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopiedField(fieldName);
      setTimeout(() => setCopiedField(null), 2500);
    } catch (err) {
      console.error('Clipboard copy failed:', err);
    }
  };

  const generateCppHeader = (container) => {
    if (!container) return '';
    return `// SICRA - Configuración de Nodo Sensor ESP32
#define DEVICE_TOKEN       "${container.device_token}"
#define CONTAINER_CAPACITY ${Number(container.capacity_liters).toFixed(1)}f  // Litros
#define TARE_WEIGHT_KG     ${Number(container.tare_weight_kg).toFixed(2)}f   // kg
#define OIL_DENSITY        ${Number(container.oil_density_kg_l).toFixed(2)}f   // kg/L`;
  };

  const handleCreateContainer = async (e) => {
    e.preventDefault();
    if (!form.business_id) {
      setError('Por favor busca y selecciona un comercio para asignarle el contenedor.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        business_id: form.business_id,
        capacity_liters: Number(form.capacity_liters),
        tare_weight_kg: Number(form.tare_weight_kg),
        oil_density_kg_l: Number(form.oil_density_kg_l)
      };

      const result = await createContainer(payload);
      setCreatedContainer(result);
      setStep(2);
      setLoading(false);
      if (onSuccess) {
        onSuccess(result);
      }
    } catch (err) {
      setLoading(false);
      setError(err.message || 'Error al aprovisionar el contenedor.');
    }
  };

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) {
          handleClose();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="container-modal-title"
    >
      <div className="modal-card" style={{ maxWidth: step === 2 ? '580px' : '540px' }}>
        {step === 1 ? (
          <>
            <div style={{ marginBottom: '20px' }}>
              <h2 id="container-modal-title" style={{ margin: '0 0 6px', fontSize: '22px' }}>
                Aprovisionar nuevo contenedor
              </h2>
              <div className="sm mut" style={{ fontSize: '13px' }}>
                Asigna un contenedor inteligente a un comercio y genera sus credenciales de telemetría.
              </div>
            </div>

            <form onSubmit={handleCreateContainer}>
              {/* 1. Buscador de Comercio (Escala para miles de establecimientos) */}
              <div className="form-group">
                <label>Comercio asignado *</label>

                {selectedBusiness ? (
                  <div
                    style={{
                      background: 'var(--nt)',
                      border: '1px solid var(--line)',
                      borderRadius: '8px',
                      padding: '12px 14px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--ink)' }}>
                        {selectedBusiness.name}
                      </div>
                      <div className="sm mut" style={{ fontSize: '12px', marginTop: '2px' }}>
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
                      autoFocus
                    />

                    {/* Results dropdown list */}
                    <div
                      style={{
                        marginTop: '6px',
                        border: '1px solid var(--line)',
                        borderRadius: '8px',
                        maxHeight: '190px',
                        overflowY: 'auto',
                        background: 'var(--card)',
                        boxShadow: '0 4px 16px rgba(0,0,0,0.08)'
                      }}
                    >
                      {isSearching ? (
                        <div className="sm mut" style={{ padding: '12px', textAlign: 'center' }}>
                          Buscando comercios…
                        </div>
                      ) : filteredBusinesses.length === 0 ? (
                        <div className="sm mut" style={{ padding: '14px', textAlign: 'center' }}>
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
                              padding: '10px 14px',
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
                            <div className="sm mut" style={{ fontSize: '11px', marginTop: '2px' }}>
                              {b.address} · {b.city}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* 2. Capacidad del Bidón PEAD */}
              <div className="form-group" style={{ marginTop: '18px' }}>
                <label>Capacidad del bidón PEAD *</label>
                <div className="row" style={{ gap: '8px' }}>
                  {[3, 20, 50, 100].map((cap) => {
                    const isSelected = Number(form.capacity_liters) === cap;
                    return (
                      <button
                        key={cap}
                        type="button"
                        className={`btn ${isSelected ? 'p' : ''}`}
                        onClick={() => {
                          const tares = { 3: 0.35, 20: 2.2, 50: 3.8, 100: 6.5 };
                          setForm({
                            ...form,
                            capacity_liters: cap,
                            tare_weight_kg: tares[cap] || 3.8
                          });
                        }}
                        style={{
                          flex: 1,
                          justifyContent: 'center',
                          padding: '9px 4px',
                          fontSize: '13px',
                          whiteSpace: 'nowrap'
                        }}
                      >
                        {cap} Litros
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 3. Peso Tara y Densidad (2 columnas) */}
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label htmlFor="tare-weight">Peso tara calibrada (kg) *</label>
                  <input
                    id="tare-weight"
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    className="form-control"
                    required
                    value={form.tare_weight_kg}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        tare_weight_kg: parseFloat(e.target.value) || 0
                      })
                    }
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="oil-density">Densidad aceite (kg/L) *</label>
                  <input
                    id="oil-density"
                    type="number"
                    step="0.01"
                    min="0.5"
                    max="1.5"
                    className="form-control"
                    required
                    value={form.oil_density_kg_l}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        oil_density_kg_l: parseFloat(e.target.value) || 0.92
                      })
                    }
                  />
                </div>
              </div>

              {/* Error feedback alert */}
              {error && (
                <div
                  className="note"
                  style={{
                    background: 'color-mix(in srgb, var(--red) 12%, transparent)',
                    color: 'var(--red)',
                    border: '1px solid color-mix(in srgb, var(--red) 25%, transparent)',
                    marginTop: '14px',
                    fontSize: '13px'
                  }}
                >
                  <span>{error}</span>
                </div>
              )}

              {/* Acciones */}
              <div className="row sp" style={{ marginTop: '24px' }}>
                <Button type="button" onClick={handleClose} disabled={loading}>
                  Cancelar
                </Button>
                <Button type="submit" variant="p" disabled={loading}>
                  <span>{loading ? 'Creando…' : 'Generar Contenedor y Token'}</span>
                </Button>
              </div>
            </form>
          </>
        ) : (
          /* Step 2: The ESP32 Flashing Card */
          <div className="token-flash-view" style={{ textAlign: 'center' }}>
            <div
              className="chip"
              style={{
                background: 'var(--gt)',
                color: 'var(--g)',
                marginBottom: '12px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <CheckIcon style={{ width: '14px', height: '14px' }} />
              <span>Contenedor aprovisionado exitosamente</span>
            </div>

            <h2 style={{ fontSize: '22px', margin: '6px 0' }}>
              Token de hardware para ESP32
            </h2>
            <p
              className="sm mut"
              style={{ maxWidth: '48ch', margin: '6px auto 18px', lineHeight: 1.4 }}
            >
              Copia este token de autenticación para grabarlo en el firmware del microcontrolador
              antes de instalar el sensor en el local.
            </p>

            {/* Token Box with 1-Click Copy */}
            <div
              className="card"
              style={{
                background: 'var(--bg)',
                padding: '16px',
                textAlign: 'left',
                marginBottom: '16px',
                border: '1px solid var(--line)'
              }}
            >
              <div className="row sp" style={{ marginBottom: '8px' }}>
                <span className="sm mut" style={{ fontWeight: 600, fontSize: '11px', letterSpacing: '0.04em' }}>
                  DEVICE TOKEN (IoT)
                </span>
                <button
                  type="button"
                  className="btn sm p"
                  onClick={() => copyToClipboard(createdContainer?.device_token || '', 'token')}
                  style={{ padding: '4px 10px', fontSize: '12px' }}
                >
                  <CheckIcon style={{ width: '13px', height: '13px' }} />
                  <span>{copiedField === 'token' ? '¡Copiado!' : 'Copiar Token'}</span>
                </button>
              </div>
              <code
                style={{
                  fontSize: '13px',
                  color: 'var(--ink)',
                  wordBreak: 'break-all',
                  fontWeight: 600,
                  fontFamily: 'monospace'
                }}
              >
                {createdContainer?.device_token}
              </code>
            </div>

            {/* C / Arduino Header Snippet */}
            <div
              className="card"
              style={{
                background: '#1B2A66',
                color: '#F2F2F2',
                padding: '16px',
                textAlign: 'left',
                border: 'none',
                boxShadow: '0 8px 24px rgba(0,0,0,0.2)'
              }}
            >
              <div className="row sp" style={{ marginBottom: '8px' }}>
                <span className="sm" style={{ color: '#E0A81E', fontWeight: 600, fontSize: '11px', letterSpacing: '0.04em' }}>
                  CÓDIGO ARDUINO / ESP32
                </span>
                <button
                  type="button"
                  className="btn sm"
                  style={{
                    background: 'rgba(255,255,255,0.18)',
                    color: '#fff',
                    border: '1px solid rgba(255,255,255,0.3)',
                    padding: '4px 10px',
                    fontSize: '12px'
                  }}
                  onClick={() => copyToClipboard(generateCppHeader(createdContainer), 'code')}
                >
                  <span>{copiedField === 'code' ? '¡Copiado!' : 'Copiar Código C'}</span>
                </button>
              </div>
              <pre
                style={{
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  overflowX: 'auto',
                  margin: 0,
                  lineHeight: 1.5,
                  color: '#E0E7FF'
                }}
              >
                {generateCppHeader(createdContainer)}
              </pre>
            </div>

            <div className="row" style={{ justifyContent: 'center', marginTop: '24px' }}>
              <Button onClick={handleClose}>
                Finalizar y cerrar
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default AddContainerModal;
