import React, { useState } from 'react';
import Header from './components/layout/Header';
import { AdminDashboard } from './components/admin';
import {
  Button,
  Card,
  StatWidget,
  BellIcon,
  ShieldIcon,
  ClockIcon,
  BatteryIcon,
  RouteIcon,
  DownloadIcon,
  ExpandIcon,
  TruckIcon
} from './components/common';

export function App() {
  const [role, setRole] = useState('admin');

  return (
    <div className="app">
      <Header role={role} setRole={setRole} />

      <main>
        {role === 'admin' && <AdminDashboard />}

        {role === 'col' && (
          <section id="col">
            <div className="row sp" style={{ alignItems: 'flex-end' }}>
              <div>
                <h1>Ruta de hoy</h1>
              </div>
              <div className="row">
                <Button icon={<DownloadIcon />}>
                  Exportar ruta
                </Button>
                <Button variant="p" icon={<RouteIcon />}>
                  Generar ruta de hoy
                </Button>
              </div>
            </div>

            <div className="grid g2" style={{ margin: '32px 0 16px' }}>
              <Card style={{ padding: '12px' }}>
                <div className="mapbox">
                  <Button className="xp" icon={<ExpandIcon />}>
                    Expandir
                  </Button>
                  <div
                    className="map"
                    style={{
                      height: '300px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    <span className="sm mut">
                      Mapa Leaflet interactivo listo para despacho cartográfico
                    </span>
                  </div>
                </div>
                <div className="row sp sm mut" style={{ padding: '12px 8px 4px' }}>
                  <span>14,8 km en total</span>
                  <span>285 L estimados</span>
                  <span>5 paradas</span>
                </div>
              </Card>

              <Card>
                <h2>Paradas Programadas</h2>
                <div style={{ marginTop: '14px' }}>
                  <div className="note" style={{ background: 'var(--nt)' }}>
                    <BellIcon />
                    <span>Alertas activas: <b>3</b> contenedores sobre el 80%</span>
                  </div>
                </div>
              </Card>
            </div>
          </section>
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
