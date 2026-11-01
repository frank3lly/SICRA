import React, { useState, useEffect } from 'react';
import { Card, Button, RouteIcon } from '../common';
import { RouteMap } from './RouteMap';
import { StopsList } from './StopsList';
import { ExportMenu } from './ExportMenu';
import {
  fetchTodayRoute,
  generateTodayRoute,
  confirmRouteStop,
  fetchContainers
} from '../../services/api';

/**
 * Collector Route Dispatch Dashboard
 * Equips truck operators with interactive Leaflet routing and pickup confirmation
 */
export function CollectorDashboard() {
  const [route, setRoute] = useState(null);
  const [activeAlertsCount, setActiveAlertsCount] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [confirmingBusinessId, setConfirmingBusinessId] = useState(null);

  // Load active route for today and containers count
  useEffect(() => {
    let mounted = true;

    async function loadData() {
      const [routeRes, containersRes] = await Promise.all([
        fetchTodayRoute(),
        fetchContainers()
      ]);

      if (mounted) {
        if (routeRes.route) {
          setRoute(routeRes.route);
        }
        if (containersRes.containers) {
          const alerts = containersRes.containers.filter(
            (c) => (c.current_fill_percentage ?? 0) >= 80
          ).length;
          setActiveAlertsCount(alerts);
        }
      }
    }

    loadData();
    return () => {
      mounted = false;
    };
  }, []);

  const handleGenerateRoute = async () => {
    setIsGenerating(true);
    try {
      const newRoute = await generateTodayRoute();
      setRoute(newRoute);
    } catch (err) {
      console.error('Failed to generate route:', err);
      alert('No se pudo generar la ruta de hoy. Verifique la conexión con el servidor.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleConfirmStop = async (businessId) => {
    const routeId = route?.route_id || route?.id;
    if (!routeId) return;
    setConfirmingBusinessId(businessId);

    try {
      await confirmRouteStop(routeId, businessId);

      // Immediately mark as visited in local state
      setRoute((prev) => {
        if (!prev) return prev;
        const updatedItinerary = prev.itinerary.map((stop) => {
          if (stop.business_id === businessId) {
            return { ...stop, visited: true, visited_at: new Date().toISOString() };
          }
          return stop;
        });
        return {
          ...prev,
          itinerary: updatedItinerary
        };
      });

      // Decrement active alerts count if applicable
      setActiveAlertsCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Failed to confirm stop:', err);
      alert('No se pudo registrar la recolección en el servidor.');
    } finally {
      setConfirmingBusinessId(null);
    }
  };

  const nonDepotStops = route?.itinerary?.filter((s) => !s.is_depot) || [];

  return (
    <section id="col">
      <div className="row sp" style={{ alignItems: 'flex-end' }}>
        <div>
          <h1>Ruta de hoy</h1>
          <div className="sm mut" style={{ marginTop: '4px' }}>
            Itinerario de recogida optimizado para San Pedro de Macorís
          </div>
        </div>
        <div className="row" style={{ gap: '10px' }}>
          <ExportMenu
            itinerary={route?.itinerary || []}
            routeId={route?.route_id || route?.id || ''}
          />
          <Button
            variant="p"
            icon={<RouteIcon />}
            disabled={isGenerating}
            onClick={handleGenerateRoute}
          >
            <span>{isGenerating ? 'Calculando ruta…' : 'Generar ruta de hoy'}</span>
          </Button>
        </div>
      </div>

      {!route ? (
        <Card style={{ marginTop: '32px', padding: '36px', textAlign: 'center' }}>
          <div className="sm mut" style={{ fontSize: '15px', marginBottom: '16px' }}>
            No hay una ruta generada para hoy aún.
          </div>
          <Button variant="p" icon={<RouteIcon />} onClick={handleGenerateRoute} disabled={isGenerating}>
            {isGenerating ? 'Calculando ruta…' : 'Generar ruta de hoy'}
          </Button>
        </Card>
      ) : (
        <div className="grid g2" style={{ marginTop: '28px' }}>
          <Card style={{ padding: '12px' }}>
            <RouteMap
              itinerary={route.itinerary || []}
              totalDistanceKm={route.total_distance_km || 0}
              totalEstimatedLiters={route.total_estimated_liters || 0}
              totalStops={route.total_stops || nonDepotStops.length}
            />
          </Card>

          <StopsList
            stops={nonDepotStops}
            onConfirm={handleConfirmStop}
            confirmingId={confirmingBusinessId}
            activeAlertsCount={activeAlertsCount}
          />
        </div>
      )}
    </section>
  );
}

export default CollectorDashboard;
