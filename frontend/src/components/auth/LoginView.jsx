import React, { useState } from 'react';
import { Card, Button } from '../common';
import { loginUser } from '../../services/api';

/**
 * Official Login Screen for SICRA Platform
 * Production-grade secure authentication gateway.
 */
export function LoginView({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!email || !password) {
      setErrorMessage('Por favor ingrese su correo electrónico y contraseña.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    const result = await loginUser(email, password);
    setIsLoading(false);

    if (result.success) {
      if (onLoginSuccess) {
        onLoginSuccess(result.user);
      }
    } else {
      setErrorMessage(result.error);
    }
  };

  return (
    <div
      style={{
        minHeight: '80vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px 16px'
      }}
    >
      <Card
        style={{
          width: '100%',
          maxWidth: '420px',
          padding: '40px 32px',
          boxShadow: '0 16px 40px color-mix(in srgb, #1B2A66 12%, transparent)'
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <img
            src="/assets/sicra-isotype.svg"
            alt="SICRA Logo"
            style={{ width: '48px', height: '48px', margin: '0 auto 12px' }}
          />
          <h1 style={{ fontSize: '24px', margin: '0 0 6px' }}>Iniciar Sesión</h1>
          <div className="sm mut" style={{ fontSize: '13px', lineHeight: 1.4 }}>
            Plataforma de Trazabilidad y Recolección de Aceite Usado
          </div>
        </div>

        {errorMessage && (
          <div
            className="note"
            style={{
              background: 'color-mix(in srgb, var(--red) 12%, transparent)',
              color: 'var(--red)',
              border: '1px solid color-mix(in srgb, var(--red) 25%, transparent)',
              marginBottom: '20px',
              fontSize: '13px'
            }}
          >
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label
              htmlFor="login-email"
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 600,
                marginBottom: '6px',
                color: 'var(--ink)'
              }}
            >
              Correo Electrónico
            </label>
            <input
              id="login-email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="nombre@entidad.do"
              style={{
                width: '100%',
                padding: '11px 14px',
                fontSize: '14px',
                borderRadius: '8px',
                border: '1px solid var(--line)',
                background: 'var(--bg)',
                color: 'var(--ink)',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label
              htmlFor="login-password"
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 600,
                marginBottom: '6px',
                color: 'var(--ink)'
              }}
            >
              Contraseña
            </label>
            <input
              id="login-password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              style={{
                width: '100%',
                padding: '11px 14px',
                fontSize: '14px',
                borderRadius: '8px',
                border: '1px solid var(--line)',
                background: 'var(--bg)',
                color: 'var(--ink)',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <Button
            type="submit"
            variant="p"
            disabled={isLoading}
            style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
          >
            <span>{isLoading ? 'Verificando credenciales…' : 'Ingresar al Sistema'}</span>
          </Button>
        </form>
      </Card>
    </div>
  );
}

export default LoginView;
