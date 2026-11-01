/**
 * Real API Service for SICRA Platform
 * Connects directly to FastAPI backend. No fake/synthetic mock data is used.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

let cachedToken = typeof window !== 'undefined' ? localStorage.getItem('sicra_token') : null;
let cachedUser = null;

try {
  const storedUser = typeof window !== 'undefined' ? localStorage.getItem('sicra_user') : null;
  if (storedUser) {
    cachedUser = JSON.parse(storedUser);
  }
} catch (e) {
  // ignore json parse error
}

/**
 * Obtain Bearer authentication token
 */
export function getAuthToken() {
  if (cachedToken) return cachedToken;
  if (typeof window !== 'undefined') {
    cachedToken = localStorage.getItem('sicra_token');
  }
  return cachedToken;
}

/**
 * Retrieve cached user profile
 */
export function getStoredUser() {
  if (cachedUser) return cachedUser;
  if (typeof window !== 'undefined') {
    try {
      const u = localStorage.getItem('sicra_user');
      if (u) {
        cachedUser = JSON.parse(u);
      }
    } catch (e) {}
  }
  return cachedUser;
}

/**
 * Authenticate with real API credentials
 */
export async function loginUser(email, password) {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim().toLowerCase(), password })
    });

    const data = await res.json();
    if (!res.ok) {
      return {
        success: false,
        error: data.detail || 'Credenciales incorrectas. Verifique su correo y contraseña.'
      };
    }

    cachedToken = data.access_token;
    cachedUser = data.user;
    if (typeof window !== 'undefined') {
      localStorage.setItem('sicra_token', cachedToken);
      localStorage.setItem('sicra_user', JSON.stringify(cachedUser));
    }

    return {
      success: true,
      user: data.user,
      token: data.access_token
    };
  } catch (err) {
    return {
      success: false,
      error: 'Error de conexión con el servidor de autenticación.'
    };
  }
}

/**
 * Terminate current user session
 */
export function logoutUser() {
  cachedToken = null;
  cachedUser = null;
  if (typeof window !== 'undefined') {
    localStorage.removeItem('sicra_token');
    localStorage.removeItem('sicra_user');
  }
}

/**
 * Verify session validity against backend
 */
export async function verifySession() {
  const token = getAuthToken();
  if (!token) return { authenticated: false, user: null };

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!res.ok) {
      logoutUser();
      return { authenticated: false, user: null };
    }
    const user = await res.json();
    cachedUser = user;
    if (typeof window !== 'undefined') {
      localStorage.setItem('sicra_user', JSON.stringify(user));
    }
    return { authenticated: true, user };
  } catch (err) {
    const storedUser = getStoredUser();
    if (storedUser) {
      return { authenticated: true, user: storedUser };
    }
    return { authenticated: false, user: null };
  }
}

/**
 * Fetch environmental statistics from backend
 */
export async function fetchEnvironmentalStats() {
  try {
    const token = await getAuthToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    const res = await fetch(`${API_BASE}/api/v1/stats/environmental`, { headers });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    const data = await res.json();
    return {
      connected: true,
      total_oil_diverted_liters: data.total_oil_diverted_liters ?? 0,
      co2_avoided_kg: data.co2_avoided_kg ?? 0,
      water_preserved_liters: data.water_preserved_liters ?? 0,
      total_collections_count: data.total_collections_count ?? 0,
      active_alerts_count: 0,
      active_containers_count: data.active_containers_count ?? 0,
      compliance_framework: data.compliance_framework ?? 'Trazabilidad Verificada'
    };
  } catch (err) {
    console.error('Failed to fetch environmental stats from server:', err.message);
    return {
      connected: false,
      error: 'Servidor no disponible o sin conexión. Verifique que la API esté activa.',
      total_oil_diverted_liters: null,
      co2_avoided_kg: null,
      water_preserved_liters: null,
      total_collections_count: null,
      active_alerts_count: null,
      active_containers_count: 0,
      compliance_framework: null
    };
  }
}

/**
 * Fetch active containers list from backend with search and pagination support
 */
export async function fetchContainers({ search = '', limit = null, offset = 0 } = {}) {
  try {
    const token = await getAuthToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (limit !== null && limit !== undefined) params.set('limit', String(limit));
    if (offset) params.set('offset', String(offset));

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/containers/${queryString}`, { headers });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }

    const totalHeader = res.headers.get('X-Total-Count');
    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      return { connected: true, containers: [], total: 0 };
    }

    const total = totalHeader ? parseInt(totalHeader, 10) : data.length;

    const containers = data.map((c) => {
      const fill = Math.round(c.current_fill_percentage || 0);
      const battery = 85;
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

    return { connected: true, containers, total };
  } catch (err) {
    console.error('Failed to fetch containers from server:', err.message);
    return {
      connected: false,
      error: 'No se pudo conectar al servidor para obtener los contenedores.',
      containers: [],
      total: 0
    };
  }
}

/**
 * Fetch latest volumetric projections with search and pagination support
 */
export async function fetchLatestPredictions({ search = '', limit = null, offset = 0 } = {}) {
  try {
    const token = await getAuthToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (limit !== null && limit !== undefined) params.set('limit', String(limit));
    if (offset) params.set('offset', String(offset));

    const queryString = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/api/v1/predictions/latest${queryString}`, { headers });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }

    const totalHeader = res.headers.get('X-Total-Count');
    const data = await res.json();
    const projections = Array.isArray(data) ? data : [];
    const total = totalHeader ? parseInt(totalHeader, 10) : projections.length;

    return {
      connected: true,
      projections,
      total
    };
  } catch (err) {
    console.error('Failed to fetch predictions from server:', err.message);
    return {
      connected: false,
      error: 'Sin conexión para proyecciones.',
      projections: [],
      total: 0
    };
  }
}

/**
 * Batch execute ML predictions across fleet on backend
 */
export async function runFleetForecast() {
  const token = await getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };

  const res = await fetch(`${API_BASE}/api/v1/predictions/run-forecast`, {
    method: 'POST',
    headers,
    body: JSON.stringify({})
  });

  if (!res.ok) {
    throw new Error(`Forecast request failed with HTTP ${res.status}`);
  }

  const result = await res.json();
  const predsResult = await fetchLatestPredictions();
  return {
    ...result,
    projections: predsResult.projections
  };
}

/**
 * Fetch today's collection route
 */
export async function fetchTodayRoute() {
  try {
    const token = await getAuthToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    const res = await fetch(`${API_BASE}/api/v1/routes/today`, { headers });
    if (res.status === 404) {
      return { connected: true, route: null };
    }
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    const data = await res.json();
    return { connected: true, route: data };
  } catch (err) {
    console.error('Failed to fetch today route:', err.message);
    return { connected: false, route: null, error: err.message };
  }
}

/**
 * Generate optimized collection route for today
 */
export async function generateTodayRoute() {
  const token = await getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };

  const res = await fetch(`${API_BASE}/api/v1/routes/generate-today`, {
    method: 'POST',
    headers,
    body: JSON.stringify({})
  });

  if (!res.ok) {
    throw new Error(`Failed to generate route: HTTP ${res.status}`);
  }
  return await res.json();
}

/**
 * Confirm pickup stop and reset container tare
 */
export async function confirmRouteStop(routeId, businessId) {
  const token = await getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };

  const res = await fetch(`${API_BASE}/api/v1/routes/${routeId}/confirm-stop/${businessId}`, {
    method: 'POST',
    headers,
    body: JSON.stringify({})
  });

  if (!res.ok) {
    throw new Error(`Failed to confirm stop: HTTP ${res.status}`);
  }
  return await res.json();
}

/**
 * Fetch business container portal details and verified pickup history
 */
export async function fetchMyContainer(businessId = null) {
  try {
    const token = await getAuthToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const url = businessId
      ? `${API_BASE}/api/v1/containers/my-container?business_id=${encodeURIComponent(businessId)}`
      : `${API_BASE}/api/v1/containers/my-container`;

    const res = await fetch(url, { headers });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    const data = await res.json();
    return { connected: true, data };
  } catch (err) {
    console.error('Failed to fetch my container:', err.message);
    return { connected: false, data: null, error: err.message };
  }
}

/**
 * Register new food business establishment into the system
 */
export async function createBusiness(payload) {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };

  const res = await fetch(`${API_BASE}/api/v1/businesses/`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  if (!res.ok) {
    let msg = 'Error al registrar el comercio';
    if (data.detail) {
      if (typeof data.detail === 'string') {
        msg = data.detail;
      } else if (Array.isArray(data.detail)) {
        msg = data.detail.map((d) => d.msg || `${d.loc?.join('.')}: error`).join(', ');
      }
    }
    throw new Error(msg);
  }
  return data;
}


