import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '../common';

/**
 * Reusable Confirmation Dialog for Administrative Deletions
 *
 * @param {boolean} isOpen - Whether modal is visible
 * @param {string} title - Title of the modal
 * @param {string} itemName - Name or identifier of the item to delete
 * @param {string} message - Warning message or extra detail
 * @param {boolean} loading - Whether deletion is in progress
 * @param {function} onConfirm - Confirm callback
 * @param {function} onClose - Cancel/close callback
 */
export function ConfirmDeleteModal({
  isOpen,
  title = 'Confirmar eliminación',
  itemName = '',
  message = 'Esta acción eliminará el registro de forma permanente. Esta operación no se puede deshacer.',
  loading = false,
  onConfirm,
  onClose
}) {
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape' && isOpen && !loading) {
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
  }, [isOpen, loading, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.55)',
        backdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '16px'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onClose();
      }}
    >
      <div
        style={{
          background: 'var(--card, #ffffff)',
          border: '1px solid var(--border, #e2e8f0)',
          borderRadius: '12px',
          padding: '28px',
          maxWidth: '460px',
          width: '100%',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              background: 'color-mix(in srgb, var(--red, #b91c1c) 12%, transparent)',
              color: 'var(--red, #b91c1c)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 6h18" />
              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
              <line x1="10" y1="11" x2="10" y2="17" />
              <line x1="14" y1="11" x2="14" y2="17" />
            </svg>
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: 'var(--ink, #0f172a)' }}>
              {title}
            </h3>
          </div>
        </div>

        {itemName && (
          <div
            style={{
              padding: '10px 14px',
              background: 'var(--nt, #f8fafc)',
              borderRadius: '6px',
              border: '1px solid var(--border, #e2e8f0)',
              marginBottom: '14px',
              fontSize: '13px',
              fontWeight: 600,
              color: 'var(--ink, #0f172a)'
            }}
          >
            {itemName}
          </div>
        )}

        <p style={{ margin: '0 0 24px', fontSize: '14px', color: 'var(--mut, #64748b)', lineHeight: '1.5' }}>
          {message}
        </p>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <Button
            type="button"
            variant="s"
            disabled={loading}
            onClick={onClose}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            variant="p"
            disabled={loading}
            onClick={onConfirm}
            style={{
              background: 'var(--red, #b91c1c)',
              borderColor: 'var(--red, #b91c1c)',
              color: '#ffffff'
            }}
          >
            {loading ? 'Eliminando…' : 'Eliminar permanentemente'}
          </Button>
        </div>
      </div>
    </div>,
    document.body
  );
}

export default ConfirmDeleteModal;
