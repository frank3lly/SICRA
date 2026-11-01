import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, Popup, AttributionControl, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Button, ExpandIcon } from '../common';
import 'leaflet/dist/leaflet.css';

// Helper component to invalidate map size upon fullscreen expansion or resize
function MapResizer({ isFullscreen }) {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 200);
    return () => clearTimeout(timer);
  }, [isFullscreen, map]);
  return null;
}

const createStopIcon = (number, isDone) => {
  const checkSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
  return L.divIcon({
    className: 'custom-stop-marker',
    html: `<div class="n-dot" style="background: ${
      isDone ? '#5D8054' : '#998937'
    }; width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; color: #fff; font-weight: 600; font-size: 13px; box-shadow: 0 2px 6px rgba(0,0,0,0.28);">${
      isDone ? checkSvg : number
    }</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14]
  });
};

const createDepotIcon = () => {
  const hubSvg = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>';
  return L.divIcon({
    className: 'custom-depot-marker',
    html: `<div style="background: #1B2A66; width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center; color: #fff; font-weight: 700; font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.35); border: 2px solid #fff;">${hubSvg}</div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  });
};

/**
 * Interactive Leaflet Route Map with Fullscreen Modal Expand and Custom Markers
 * @param {Array<object>} itinerary - Sequence of stops including depot
 * @param {number} totalDistanceKm - Total route distance in km
 * @param {number} totalEstimatedLiters - Total estimated oil volume in liters
 * @param {number} totalStops - Count of business stops
 */
export function RouteMap({
  itinerary = [],
  totalDistanceKm = 0,
  totalEstimatedLiters = 0,
  totalStops = 0
}) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Close fullscreen on Escape
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreen]);

  // Center of San Pedro de Macorís
  const defaultCenter = [18.455, -69.305];

  // Coordinates sequence for polyline
  const polylineCoords = itinerary.map((s) => [s.latitude, s.longitude]);

  // Non-depot stops
  const stops = itinerary.filter((s) => !s.is_depot);
  const depot = itinerary.find((s) => s.is_depot) || {
    latitude: 18.465,
    longitude: -69.295,
    business_name: 'Reoil SPM Depot',
    address: 'Zona Industrial SPM'
  };

  return (
    <div className={`mapbox ${isFullscreen ? 'full' : ''}`} id="mapbox">
      <Button
        className="xp"
        id="xp"
        icon={<ExpandIcon />}
        onClick={() => setIsFullscreen((prev) => !prev)}
        aria-label={isFullscreen ? 'Cerrar pantalla completa' : 'Expandir mapa'}
      >
        <span>{isFullscreen ? 'Cerrar' : 'Expandir'}</span>
      </Button>

      <div className="map" style={{ height: isFullscreen ? '100%' : '380px' }}>
        <MapContainer
          center={defaultCenter}
          zoom={14}
          scrollWheelZoom={true}
          attributionControl={false}
          style={{ width: '100%', height: '100%', minHeight: '300px' }}
        >
          <AttributionControl prefix={false} />
          <MapResizer isFullscreen={isFullscreen} />

          {/* CartoDB Positron / OSM Tiles */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Route Trajectory Polyline */}
          {polylineCoords.length > 1 && (
            <Polyline
              positions={polylineCoords}
              color="#5D8054"
              weight={4}
              dashArray="6, 8"
            />
          )}

          {/* Central Depot Hub Marker */}
          <Marker
            position={[depot.latitude, depot.longitude]}
            icon={createDepotIcon()}
          >
            <Popup>
              <b>{depot.business_name}</b>
              <div style={{ fontSize: '12px', color: '#666' }}>{depot.address}</div>
              <div style={{ fontSize: '12px', marginTop: '4px', fontWeight: 600 }}>
                Centro Logístico de Despacho
              </div>
            </Popup>
          </Marker>

          {/* Ordered Business Stops */}
          {stops.map((stop, idx) => {
            const isDone = Boolean(stop.visited);
            const stopNumber = idx + 1;

            return (
              <Marker
                key={stop.business_id || idx}
                position={[stop.latitude, stop.longitude]}
                icon={createStopIcon(stopNumber, isDone)}
              >
                <Popup>
                  <div style={{ fontWeight: 600 }}>
                    Parada {stopNumber}: {stop.business_name}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666' }}>{stop.address}</div>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>
                    Volumen estimado: <b>{stop.estimated_liters} L</b>
                  </div>
                  <div style={{ fontSize: '12px', marginTop: '2px' }}>
                    Estado:{' '}
                    <span style={{ color: isDone ? '#5D8054' : '#E0A81E', fontWeight: 600 }}>
                      {isDone ? 'Vaciado completado' : 'Pendiente de recogida'}
                    </span>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

      <div className="row sp sm mut" style={{ padding: '12px 8px 4px' }}>
        <span>{totalDistanceKm} km en total</span>
        <span>{totalEstimatedLiters} L estimados</span>
        <span>{totalStops} paradas</span>
      </div>
    </div>
  );
}

export default RouteMap;
