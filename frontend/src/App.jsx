import React, { useState, useEffect } from 'react';
import Header from './components/layout/Header';
import { LoginView } from './components/auth';
import { AdminDashboard, ForecastCenter } from './components/admin';
import { CollectorDashboard } from './components/collector';
import { BusinessDashboard } from './components/business';
import { getStoredUser, verifySession, logoutUser } from './services/api';

export function App() {
  const [user, setUser] = useState(() => getStoredUser());
  const [isVerifying, setIsVerifying] = useState(true);
  const [adminSubView, setAdminSubView] = useState('overview'); // 'overview' | 'forecast'

  // Verify session on initial mount
  useEffect(() => {
    let mounted = true;

    async function checkAuth() {
      const session = await verifySession();
      if (mounted) {
        if (session.authenticated && session.user) {
          setUser(session.user);
        } else {
          setUser(null);
        }
        setIsVerifying(false);
      }
    }

    checkAuth();
    return () => {
      mounted = false;
    };
  }, []);

  const handleLoginSuccess = (loggedInUser) => {
    setUser(loggedInUser);
    setAdminSubView('overview');
  };

  const handleLogout = () => {
    logoutUser();
    setUser(null);
    setAdminSubView('overview');
  };

  return (
    <div className="app">
      {/* Ambient Brand Watermarks with fading effect in the background */}
      <div className="brand-watermark-drop" aria-hidden="true" />
      <div className="brand-watermark-recycle" aria-hidden="true" />

      <Header
        user={user}
        onBrandClick={() => setAdminSubView('overview')}
        onLogout={handleLogout}
      />

      <main>
        {isVerifying ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--mut)' }}>
            <div className="sm">Verificando sesión…</div>
          </div>
        ) : !user ? (
          <LoginView onLoginSuccess={handleLoginSuccess} />
        ) : (
          <>
            {/* Business Owner view: strictly isolated to their establishment */}
            {user.role === 'BUSINESS_OWNER' && (
              <BusinessDashboard />
            )}

            {/* Collector view: strictly isolated to routing and dispatch */}
            {user.role === 'COLLECTOR' && (
              <CollectorDashboard />
            )}

            {/* Admin view: strictly isolated to administrative overview and forecasting */}
            {user.role === 'ADMIN' && (
              adminSubView === 'forecast' ? (
                <ForecastCenter onBack={() => setAdminSubView('overview')} />
              ) : (
                <AdminDashboard onOpenForecast={() => setAdminSubView('forecast')} />
              )
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
