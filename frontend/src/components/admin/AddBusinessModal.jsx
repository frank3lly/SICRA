import React, { useState, useEffect } from 'react';
import { Button } from '../common';
import { createBusiness } from '../../services/api';

/**
 * Clean Modal Form for Registering New Food Business Establishments
 *
 * @param {boolean} isOpen - Whether the modal is rendered
 * @param {function} onClose - Modal close handler
 * @param {function} onSuccess - Callback when establishment is successfully registered
 */
export function AddBusinessModal({ isOpen, onClose, onSuccess }) {
  const initialForm = {
    name: '',
    business_type: 'PICA_POLLO',
    num_fryers: 2,
    avg_daily_customers: 100,
    phone: '',
    address: '',
    city: 'San Pedro de Macorís',
    latitude: 18.4552,
    longitude: -69.3087,
    is_active: true
  };

  const [form, setForm] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const setCoords = (lat, lng) => {
    setForm((prev) => ({
      ...prev,
      latitude: lat,
      longitude: lng
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!form.name.trim()) {
      setError('Por favor ingresa el nombre del comercio.');
      return;
    }
    if (!form.address.trim()) {
      setError('Por favor ingresa la dirección física.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        name: form.name.trim(),
        business_type: form.business_type,
        num_fryers: Number(form.num_fryers) || 1,
        avg_daily_customers: Number(form.avg_daily_customers) || 10,
        address: form.address.trim(),
        city: form.city.trim() || 'San Pedro de Macorís',
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        phone: form.phone.trim() || null,
        is_active: true
      };

      const created = await createBusiness(payload);
      setSubmitting(false);
      setForm(initialForm);
      if (onSuccess) {
        onSuccess(created);
      }
      onClose();
    } catch (err) {
      setSubmitting(false);
      setError(err.message || 'Error al guardar el comercio.');
    }
  };

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) {
          onClose();
        }
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div className="modal-card">
        <div style={{ marginBottom: '20px' }}>
          <h2 id="modal-title" style={{ margin: '0 0 6px', fontSize: '22px' }}>
            Registrar nuevo comercio
          </h2>
          <div className="sm mut" style={{ fontSize: '13px' }}>
            Ingresa los datos del establecimiento para integrarlo a la red de recolección.
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {/* 1. Nombre comercial */}
          <div className="form-group">
            <label htmlFor="biz-name">Nombre del comercio *</label>
            <input
              id="biz-name"
              type="text"
              className="form-control"
              required
              placeholder="Ej. Pica Pollo Expreso"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>

          {/* 2. Tipo y Calderos (2 columnas) */}
          <div className="grid" style={{ gridTemplateColumns: '1.4fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label htmlFor="biz-type">Tipo de negocio *</label>
              <select
                id="biz-type"
                className="form-control"
                value={form.business_type}
                onChange={(e) => setForm({ ...form, business_type: e.target.value })}
              >
                <option value="PICA_POLLO">Pica Pollo (Pollo frito)</option>
                <option value="FRITURA">Fritura (Chimi / Frituras)</option>
                <option value="CAFETERIA">Cafetería / Empanadas</option>
                <option value="RESTAURANTE">Restaurante formal</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="biz-fryers">No. Calderos / Freidoras *</label>
              <input
                id="biz-fryers"
                type="number"
                className="form-control"
                min="1"
                max="15"
                required
                value={form.num_fryers}
                onChange={(e) =>
                  setForm({ ...form, num_fryers: parseInt(e.target.value, 10) || 1 })
                }
              />
            </div>
          </div>

          {/* 3. Clientes y Teléfono (2 columnas) */}
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label htmlFor="biz-customers">Clientes prom. por día *</label>
              <input
                id="biz-customers"
                type="number"
                className="form-control"
                min="10"
                required
                value={form.avg_daily_customers}
                onChange={(e) =>
                  setForm({ ...form, avg_daily_customers: parseInt(e.target.value, 10) || 10 })
                }
              />
            </div>

            <div className="form-group">
              <label htmlFor="biz-phone">Teléfono de contacto</label>
              <input
                id="biz-phone"
                type="tel"
                className="form-control"
                placeholder="809-529-0000"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </div>
          </div>

          {/* 4. Dirección */}
          <div className="form-group">
            <label htmlFor="biz-address">Dirección física *</label>
            <input
              id="biz-address"
              type="text"
              className="form-control"
              required
              placeholder="Calle, número y sector"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </div>

          {/* 5. Ubicación GPS con Presets de San Pedro de Macorís */}
          <div className="form-group">
            <div className="row sp" style={{ marginBottom: '6px' }}>
              <label style={{ margin: 0 }}>Coordenadas GPS *</label>
              <div className="row" style={{ gap: '4px' }}>
                <button
                  type="button"
                  className="chip"
                  onClick={() => setCoords(18.4538, -69.3095)}
                  title="Universidad Central del Este"
                >
                  UCE
                </button>
                <button
                  type="button"
                  className="chip"
                  onClick={() => setCoords(18.4485, -69.302)}
                  title="Malecón SPM"
                >
                  Malecón
                </button>
                <button
                  type="button"
                  className="chip"
                  onClick={() => setCoords(18.461, -69.3012)}
                  title="Barrio Lindo"
                >
                  B. Lindo
                </button>
                <button
                  type="button"
                  className="chip"
                  onClick={() => setCoords(18.4552, -69.3087)}
                  title="Centro Histórico"
                >
                  Centro
                </button>
              </div>
            </div>

            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <input
                type="number"
                step="0.0001"
                className="form-control"
                placeholder="Latitud (ej. 18.4552)"
                required
                value={form.latitude}
                onChange={(e) =>
                  setForm({ ...form, latitude: parseFloat(e.target.value) || 0 })
                }
              />
              <input
                type="number"
                step="0.0001"
                className="form-control"
                placeholder="Longitud (ej. -69.3087)"
                required
                value={form.longitude}
                onChange={(e) =>
                  setForm({ ...form, longitude: parseFloat(e.target.value) || 0 })
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

          {/* 6. Botones de acción */}
          <div className="row sp" style={{ marginTop: '24px' }}>
            <Button type="button" onClick={onClose} disabled={submitting}>
              Cancelar
            </Button>
            <Button type="submit" variant="p" disabled={submitting}>
              <span>{submitting ? 'Guardando…' : 'Guardar comercio'}</span>
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddBusinessModal;
