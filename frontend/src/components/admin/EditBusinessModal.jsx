import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '../common';
import { updateBusiness } from '../../services/api';

/**
 * Modal Form for Editing Existing Business Establishments (Admin only)
 *
 * @param {boolean} isOpen - Whether the modal is rendered
 * @param {object} business - The business record to edit
 * @param {function} onClose - Modal close handler
 * @param {function} onSuccess - Callback when establishment is successfully updated
 */
export function EditBusinessModal({ isOpen, business, onClose, onSuccess }) {
  const [form, setForm] = useState({
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
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (business) {
      setForm({
        name: business.name || '',
        business_type: business.business_type || 'PICA_POLLO',
        num_fryers: business.num_fryers ?? 2,
        avg_daily_customers: business.avg_daily_customers ?? 100,
        phone: business.phone || '',
        address: business.address || '',
        city: business.city || 'San Pedro de Macorís',
        latitude: business.latitude ?? 18.4552,
        longitude: business.longitude ?? -69.3087,
        is_active: business.is_active ?? true
      });
      setError(null);
    }
  }, [business, isOpen]);

  // Close on Escape key
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

  if (!isOpen || !business) return null;

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
        is_active: Boolean(form.is_active)
      };

      const updated = await updateBusiness(business.id, payload);
      setSubmitting(false);
      if (onSuccess) {
        onSuccess(updated);
      }
      onClose();
    } catch (err) {
      setSubmitting(false);
      setError(err.message || 'Error al actualizar el comercio.');
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
      aria-labelledby="edit-biz-modal-title"
    >
      <div className="modal-card">
        <div style={{ marginBottom: '20px' }}>
          <h2 id="edit-biz-modal-title" style={{ margin: '0 0 6px', fontSize: '22px' }}>
            Editar comercio
          </h2>
          <div className="sm mut" style={{ fontSize: '13px' }}>
            Modifica los parámetros operativos y de contacto del establecimiento.
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Nombre comercial */}
          <div className="form-group">
            <label htmlFor="edit-biz-name">Nombre del comercio *</label>
            <input
              id="edit-biz-name"
              type="text"
              className="form-control"
              required
              placeholder="Ej. Pica Pollo Expreso"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>

          {/* Tipo y Calderos (2 columnas) */}
          <div className="grid" style={{ gridTemplateColumns: '1.4fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label htmlFor="edit-biz-type">Tipo de negocio *</label>
              <select
                id="edit-biz-type"
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
              <label htmlFor="edit-biz-fryers">No. Calderos / Freidoras *</label>
              <input
                id="edit-biz-fryers"
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

          {/* Clientes y Teléfono (2 columnas) */}
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label htmlFor="edit-biz-customers">Clientes prom. por día *</label>
              <input
                id="edit-biz-customers"
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
              <label htmlFor="edit-biz-phone">Teléfono de contacto</label>
              <input
                id="edit-biz-phone"
                type="tel"
                className="form-control"
                placeholder="809-529-0000"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </div>
          </div>

          {/* Dirección */}
          <div className="form-group">
            <label htmlFor="edit-biz-address">Dirección física *</label>
            <input
              id="edit-biz-address"
              type="text"
              className="form-control"
              required
              placeholder="Calle, número y sector"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
            />
          </div>

          {/* Ubicación GPS con Presets */}
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
                placeholder="Latitud (18.xxxx)"
                required
                value={form.latitude}
                onChange={(e) => setForm({ ...form, latitude: parseFloat(e.target.value) || 0 })}
              />
              <input
                type="number"
                step="0.0001"
                className="form-control"
                placeholder="Longitud (-69.xxxx)"
                required
                value={form.longitude}
                onChange={(e) => setForm({ ...form, longitude: parseFloat(e.target.value) || 0 })}
              />
            </div>
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
              <span>Comercio activo en la red de recolección</span>
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

export default EditBusinessModal;
