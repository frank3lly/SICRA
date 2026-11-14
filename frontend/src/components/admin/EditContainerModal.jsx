import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '../common';
import { updateContainer } from '../../services/api';

/**
 * Modal for Editing Smart Container Calibrations and Status (Admin only)
 *
 * @param {boolean} isOpen - Whether modal is open
 * @param {object} container - Container record being edited
 * @param {function} onClose - Close callback
 * @param {function} onSuccess - Callback when container is updated
 */
export function EditContainerModal({ isOpen, container, onClose, onSuccess }) {
  const [form, setForm] = useState({
    capacity_liters: 50,
    tare_weight_kg: 3.8,
    oil_density_kg_l: 0.92,
    status: 'ACTIVE'
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (container) {
      setForm({
        capacity_liters: container.capacity_liters ?? 50,
        tare_weight_kg: container.tare_weight_kg ?? 3.8,
        oil_density_kg_l: container.oil_density_kg_l ?? 0.92,
        status: container.status || 'ACTIVE'
      });
      setError(null);
    }
  }, [container, isOpen]);

  // Handle escape key
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

  if (!isOpen || !container) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const cap = parseFloat(form.capacity_liters);
    const tare = parseFloat(form.tare_weight_kg);
    const density = parseFloat(form.oil_density_kg_l);

    if (isNaN(cap) || cap <= 0) {
      setError('La capacidad debe ser un número positivo.');
      return;
    }
    if (isNaN(tare) || tare < 0) {
      setError('El peso de tara debe ser un número válido.');
      return;
    }
    if (isNaN(density) || density <= 0) {
      setError('La densidad del aceite debe ser mayor a 0.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        capacity_liters: cap,
        tare_weight_kg: tare,
        oil_density_kg_l: density,
        status: form.status
      };

      const updated = await updateContainer(container.id, payload);
      setSubmitting(false);
      if (onSuccess) {
        onSuccess(updated);
      }
      onClose();
    } catch (err) {
      setSubmitting(false);
      setError(err.message || 'Error al actualizar el contenedor.');
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
      aria-labelledby="edit-container-title"
    >
      <div className="modal-card">
        <div style={{ marginBottom: '20px' }}>
          <h2 id="edit-container-title" style={{ margin: '0 0 6px', fontSize: '22px' }}>
            Editar Contenedor IoT
          </h2>
          <div className="sm mut" style={{ fontSize: '13px' }}>
            {container.business_name
              ? `Asignado a: ${container.business_name}`
              : `ID: ${container.id?.slice(0, 8)}…`}
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Capacidad y Estado */}
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label htmlFor="edit-capacity">Capacidad máxima (L) *</label>
              <input
                id="edit-capacity"
                type="number"
                step="0.5"
                min="5"
                max="5000"
                className="form-control"
                required
                value={form.capacity_liters}
                onChange={(e) => setForm({ ...form, capacity_liters: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label htmlFor="edit-status">Estado Operativo *</label>
              <select
                id="edit-status"
                className="form-control"
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                <option value="ACTIVE">Activo en servicio</option>
                <option value="MAINTENANCE">En mantenimiento</option>
                <option value="RETIRED">Retirado / Inactivo</option>
              </select>
            </div>
          </div>

          {/* Calibración de Hardware: Tara y Densidad */}
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label htmlFor="edit-tare">Peso de Tara (kg) *</label>
              <input
                id="edit-tare"
                type="number"
                step="0.01"
                min="0"
                className="form-control"
                required
                value={form.tare_weight_kg}
                onChange={(e) => setForm({ ...form, tare_weight_kg: e.target.value })}
              />
              <span className="sm mut" style={{ fontSize: '11px', display: 'block', marginTop: '4px' }}>
                Peso del contenedor vacío en celda de carga HX711
              </span>
            </div>

            <div className="form-group">
              <label htmlFor="edit-density">Densidad del Aceite (kg/L) *</label>
              <input
                id="edit-density"
                type="number"
                step="0.001"
                min="0.5"
                max="1.5"
                className="form-control"
                required
                value={form.oil_density_kg_l}
                onChange={(e) => setForm({ ...form, oil_density_kg_l: e.target.value })}
              />
              <span className="sm mut" style={{ fontSize: '11px', display: 'block', marginTop: '4px' }}>
                Estándar UCO: 0.92 kg/L
              </span>
            </div>
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

export default EditContainerModal;
