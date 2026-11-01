import React, { useState } from 'react';
import Header from './components/layout/Header';
import { AdminDashboard, ForecastCenter } from './components/admin';
import { CollectorDashboard } from './components/collector';
import {
  Card,
  StatWidget,
  ShieldIcon,
  ClockIcon,
  BatteryIcon,
  TruckIcon
} from './components/common';

export function App() {
  const [role, setRole] = useState('admin');
  const [adminSubView, setAdminSubView] = useState('overview'); // 'overview' | 'forecast'

  return (
    <div className="app">
      {/* Ambient Brand Watermarks with fading effect in the background */}
      <div className="brand-watermark-drop" aria-hidden="true" />
      <div className="brand-watermark-recycle" aria-hidden="true" />

      <Header
        role={role}
        setRole={(newRole) => {
          setRole(newRole);
          setAdminSubView('overview');
        }}
        onBrandClick={() => setAdminSubView('overview')}
      />

      <main>
        {role === 'admin' && (
          adminSubView === 'forecast' ? (
            <ForecastCenter
              onBack={() => setAdminSubView('overview')}
            />
          ) : (
            <AdminDashboard
              onOpenForecast={() => setAdminSubView('forecast')}
            />
          )
        )}

        {role === 'col' && (
          <CollectorDashboard />
        )}

        {role === 'biz' && (
          <section id="biz">
            <div className="biz">
              <h1 style={{ marginBottom: '28px' }}>Pica Pollo Expreso</h1>
              <Card style={{ padding: '30px', textAlign: 'center' }}>
                <div className="ring">
                  <svg viewBox="0 0 130 130" width="190" height="190">
                    <circle cx="65" cy="65" r="54" fill="none" stroke="var(--nt)" strokeWidth="11" />
                    <circle
                      cx="65"
                      cy="65"
                      r="54"
                      fill="none"
                      stroke="#E0A81E"
                      strokeWidth="11"
                      strokeLinecap="round"
                      strokeDasharray="281.6 339.3"
                      transform="rotate(-90 65 65)"
                    />
                  </svg>
                  <b>83%<small>41,5 de 50 L</small></b>
                </div>
                <div className="row" style={{ justifyContent: 'center', marginTop: '20px' }}>
                  <ClockIcon style={{ color: 'var(--o)' }} />
                  <span>Recolección recomendada en unas <b>18 horas</b></span>
                </div>
              </Card>

              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', marginTop: '16px' }}>
                <StatWidget
                  icon={<TruckIcon />}
                  label="Última recolección"
                  value="28 oct"
                />
                <StatWidget
                  icon={<BatteryIcon />}
                  label="Sensor"
                  value="69%"
                />
              </div>

              <div className="note" style={{ marginTop: '16px' }}>
                <ShieldIcon />
                <span>Recolecciones verificadas · Ley 225-20</span>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
