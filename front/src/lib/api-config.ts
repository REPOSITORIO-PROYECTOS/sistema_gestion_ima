// Configuración de la API
export const API_CONFIG = {
  // URL base de la API - usar variable de entorno o fallback
  BASE_URL: (process.env.NEXT_PUBLIC_API_URL ||
    (process.env.NODE_ENV === 'production'
      ? 'https://sistema-ima.sistemataup.online'
      : 'http://localhost:8000')) + '/api',

  // Endpoints
  ENDPOINTS: {
    // Mesas
    MESAS: '/mesas/obtener_todas',
    MESA_BY_ID: (id: number) => `/mesas/obtener/${id}`,
    MESA_CREATE: '/mesas/crear',
    MESA_UPDATE: (id: number) => `/mesas/actualizar/${id}`,
    MESA_DELETE: (id: number) => `/mesas/eliminar/${id}`,
    MESA_MERGE: '/mesas/unir',

    // Consumos
    CONSUMOS_ABIERTOS: (mesaId: number) => `/mesas/${mesaId}/consumos_abiertos`,
    CONSUMO_CREATE: '/mesas/consumo/crear',
    CONSUMO_ADD_DETALLE: (consumoId: number) => `/mesas/consumo/${consumoId}/agregar_detalle`,
    CONSUMO_CERRAR: (consumoId: number) => `/mesas/consumo/${consumoId}/cerrar`,
    CONSUMO_FACTURAR: (consumoId: number) => `/mesas/consumo/${consumoId}/facturar`,
    CONSUMOS_GET_ALL_ACTIVE_BY_EMPRESA: '/consumos/activos_por_empresa',

    // Tickets
    TICKET_GENERAR: '/mesas/ticket/generar',

    // Productos (para consumos)
    PRODUCTOS: '/articulos/obtener_todos',
    ARTICULO_BY_ID: (id: number) => `/articulos/obtener/${id}`,

    // Caja
    CAJA_ESTADO: '/caja/estado-actual',
  }
};

// Tipos de respuesta comunes
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// Función helper para obtener headers con autenticación
export const getAuthHeaders = (token?: string) => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return headers;
};
