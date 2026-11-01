import React, { useState, useEffect, useRef } from 'react';
import { Button, DownloadIcon } from '../common';

/**
 * Export Route Dropdown Menu
 * Provides export to Google Maps navigation, CSV, GPX, and printable PDF
 * @param {Array<object>} itinerary - Sequence of stops including depot
 * @param {string} routeId - ID of current route
 */
export function ExportMenu({ itinerary = [], routeId = '' }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  // Close popover on outside click or Escape key
  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false);
      }
    }

    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setOpen(false);
      }
    }

    if (open) {
      document.addEventListener('click', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('click', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const nonDepotStops = itinerary.filter((s) => !s.is_depot);
  const depot = itinerary.find((s) => s.is_depot) || {
    latitude: 18.465,
    longitude: -69.295,
    business_name: 'Reoil SPM Depot'
  };

  // 1. Google Maps Navigation link
  const handleOpenGoogleMaps = () => {
    if (nonDepotStops.length === 0) {
      alert('No hay paradas en la ruta para navegar.');
      return;
    }
    const origin = `${depot.latitude},${depot.longitude}`;
    const destination = origin;
    const waypoints = nonDepotStops.map((s) => `${s.latitude},${s.longitude}`).join('|');
    const url = `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}&waypoints=${encodeURIComponent(waypoints)}&travelmode=driving`;
    window.open(url, '_blank', 'noopener,noreferrer');
    setOpen(false);
  };

  // 2. CSV Export
  const handleExportCSV = () => {
    if (itinerary.length === 0) {
      alert('No hay datos de ruta para exportar.');
      return;
    }
    const rows = [
      ['Secuencia', 'Comercio', 'Direccion', 'Litros Estimados', 'Latitud', 'Longitud', 'Estado']
    ];

    itinerary.forEach((s) => {
      rows.push([
        s.sequence,
        `"${(s.business_name || '').replace(/"/g, '""')}"`,
        `"${(s.address || '').replace(/"/g, '""')}"`,
        s.estimated_liters ?? 0,
        s.latitude,
        s.longitude,
        s.visited ? 'Completado' : 'Pendiente'
      ]);
    });

    const csvContent = rows.map((r) => r.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `hoja_ruta_recoleccion_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setOpen(false);
  };

  // 3. GPX Export
  const handleExportGPX = () => {
    if (itinerary.length === 0) {
      alert('No hay datos de ruta para exportar.');
      return;
    }
    const waypointsXML = itinerary
      .map(
        (s) => `  <wpt lat="${s.latitude}" lon="${s.longitude}">
    <name>${s.sequence}. ${s.business_name}</name>
    <desc>${s.address || ''} - ${s.estimated_liters || 0} L</desc>
  </wpt>`
      )
      .join('\n');

    const gpxContent = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="SICRA Dispatch" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Ruta de Recoleccion SICRA</name>
    <time>${new Date().toISOString()}</time>
  </metadata>
${waypointsXML}
</gpx>`;

    const blob = new Blob([gpxContent], { type: 'application/gpx+xml;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `ruta_recoleccion_${new Date().toISOString().slice(0, 10)}.gpx`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setOpen(false);
  };

  // 4. Print PDF
  const handlePrint = () => {
    setOpen(false);
    setTimeout(() => {
      window.print();
    }, 150);
  };

  return (
    <div className="menu" ref={menuRef}>
      <Button
        id="ex"
        icon={<DownloadIcon />}
        onClick={(e) => {
          e.stopPropagation();
          setOpen((prev) => !prev);
        }}
      >
        Exportar ruta
      </Button>

      {open && (
        <div className="pop" id="pop">
          <button type="button" onClick={handleOpenGoogleMaps}>
            Abrir en Google Maps
          </button>
          <button type="button" onClick={handleExportCSV}>
            Hoja CSV
          </button>
          <button type="button" onClick={handleExportGPX}>
            Archivo GPX
          </button>
          <button type="button" onClick={handlePrint}>
            PDF imprimible
          </button>
        </div>
      )}
    </div>
  );
}

export default ExportMenu;
