import React, { useState } from 'react';
import Header from './components/layout/Header';
import { AdminDashboard, ForecastCenter } from './components/admin';
import { CollectorDashboard } from './components/collector';
import { BusinessDashboard } from './components/business';

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
          <BusinessDashboard />
        )}
      </main>
    </div>
  );
}

export default App;
