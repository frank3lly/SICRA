/**
 * API service for SICRA platform
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

export const DEFAULT_ENVIRONMENTAL_STATS = {
  total_oil_diverted_liters: 14250.0,
  co2_avoided_kg: 40612.5,
  water_preserved_liters: 14250000.0,
  total_collections_count: 312,
  active_alerts_count: 3,
  active_containers_count: 10,
  compliance_framework: 'Ley No. 225-20 de Gestión Integral y Coprocesamiento de Residuos'
};

export const DEFAULT_CONTAINERS = [
  {
    id: '1',
    business_name: 'Pica Pollo Expreso',
    current_fill_percentage: 83,
    battery_percentage: 69,
    status_label: 'Casi lleno',
    status_variant: 'w',
    capacity_liters: 100,
    current_volume_liters: 83
  },
  {
    id: '2',
    business_name: 'Frituras Doña Ana',
    current_fill_percentage: 96,
    battery_percentage: 54,
    status_label: 'Crítico',
    status_variant: 'c',
    capacity_liters: 50,
    current_volume_liters: 48
  },
  {
    id: '3',
    business_name: 'Cafetería Central',
    current_fill_percentage: 41,
    battery_percentage: 88,
    status_label: 'Normal',
    status_variant: '',
    capacity_liters: 20,
    current_volume_liters: 8.2
  },
  {
    id: '4',
    business_name: 'Comedor Los Pinos',
    current_fill_percentage: 22,
    battery_percentage: 91,
    status_label: 'Normal',
    status_variant: '',
    capacity_liters: 50,
    current_volume_liters: 11
  },
  {
    id: '5',
    business_name: 'Restaurante El Muelle',
    current_fill_percentage: 80,
    battery_percentage: 18,
    status_label: 'Batería baja',
    status_variant: 'w',
    capacity_liters: 100,
    current_volume_liters: 80
  }
];

export const DEFAULT_PROJECTIONS = [
  { name: 'Frituras Doña Ana', dailyLiters: 9.0, currentPct: 96, forecastPct: 100 },
  { name: 'Pica Pollo Expreso', dailyLiters: 14.2, currentPct: 83, forecastPct: 97 },
  { name: 'Restaurante El Muelle', dailyLiters: 11.0, currentPct: 80, forecastPct: 91 },
  { name: 'Cafetería Central', dailyLiters: 11.0, currentPct: 41, forecastPct: 52 },
  { name: 'Comedor Los Pinos', dailyLiters: 7.0, currentPct: 22, forecastPct: 29 }
];

export async function fetchEnvironmentalStats() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/stats/environmental`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    return {
      total_oil_diverted_liters: data.total_oil_diverted_liters ?? DEFAULT_ENVIRONMENTAL_STATS.total_oil_diverted_liters,
      co2_avoided_kg: data.co2_avoided_kg ?? DEFAULT_ENVIRONMENTAL_STATS.co2_avoided_kg,
      water_preserved_liters: data.water_preserved_liters ?? DEFAULT_ENVIRONMENTAL_STATS.water_preserved_liters,
      total_collections_count: data.total_collections_count ?? DEFAULT_ENVIRONMENTAL_STATS.total_collections_count,
      active_alerts_count: DEFAULT_ENVIRONMENTAL_STATS.active_alerts_count,
      active_containers_count: data.active_containers_count ?? DEFAULT_ENVIRONMENTAL_STATS.active_containers_count,
      compliance_framework: data.compliance_framework ?? DEFAULT_ENVIRONMENTAL_STATS.compliance_framework
    };
  } catch (err) {
    console.info('Using local environmental stats:', err.message);
    return DEFAULT_ENVIRONMENTAL_STATS;
  }
}

export async function fetchContainers() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/containers/`);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    if (Array.isArray(data) && data.length > 0) {
      return data.map((c) => {
        const fill = Math.round(c.current_fill_percentage || 0);
        const battery = 85; // Simulated IoT battery if not directly in container model
        let status_label = 'Normal';
        let status_variant = '';

        if (battery < 20) {
          status_label = 'Batería baja';
          status_variant = 'w';
        } else if (fill >= 95) {
          status_label = 'Crítico';
          status_variant = 'c';
        } else if (fill >= 80) {
          status_label = 'Casi lleno';
          status_variant = 'w';
        }

        return {
          id: c.id,
          business_name: c.business_name || 'Comercio',
          current_fill_percentage: fill,
          battery_percentage: battery,
          status_label,
          status_variant,
          capacity_liters: c.capacity_liters || 50,
          current_volume_liters: c.current_volume_liters || 0
        };
      });
    }
    return DEFAULT_CONTAINERS;
  } catch (err) {
    console.info('Using local container fleet data:', err.message);
    return DEFAULT_CONTAINERS;
  }
}

export async function runFleetForecast() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/predictions/run-forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    return await res.json();
  } catch (err) {
    console.info('Simulating forecast run locally:', err.message);
    return { status: 'forecast_completed', containers_processed: 5, predictions_generated: 5 };
  }
}
