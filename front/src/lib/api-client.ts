import { API_CONFIG, ApiResponse, getAuthHeaders } from './api-config';
import type {
  MesaCreate,
  MesaUpdate,
  ConsumoCreate,
  ConsumoDetalleCreate,
  TicketRequest,
  ConsumoMesaDetallePopulated
} from './types/mesas';
import { useAuthStore } from './authStore';

// Cliente API genérico para el backend
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_CONFIG.BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = `${this.baseUrl}${endpoint}`;
      // Obtener el token del authStore
      const token = useAuthStore.getState().token || undefined;

      const response = await fetch(url, {
        ...options,
        headers: {
          ...getAuthHeaders(token), // Ahora pasa el token
          ...options.headers,
        },
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch (jsonError) {
          console.warn("Could not parse error response as JSON:", jsonError);
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      console.error('API Error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  async download(endpoint: string, body?: unknown, headers?: Record<string, string>): Promise<Blob | null> {
    try {
      const url = `${this.baseUrl}${endpoint}`;
      const token = useAuthStore.getState().token || undefined;
      const response = await fetch(url, {
        method: 'POST',
        body: body ? JSON.stringify(body) : undefined,
        headers: {
          ...getAuthHeaders(token),
          Accept: 'application/pdf',
          ...headers,
        },
      });
      if (!response.ok) {
        if (response.status === 401) {
          useAuthStore.getState().logout();
          if (typeof window !== 'undefined') window.location.href = '/';
          throw new Error("Sesión expirada");
        }
        try {
          const err = await response.json();
          throw new Error(err?.detail || `HTTP ${response.status}: ${response.statusText}`);
        } catch (e) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
      }
      return await response.blob();
    } catch (e) {
      console.error('Download error:', e);
      return null;
    }
  }

  // Métodos HTTP
  async get<T>(endpoint: string, headers?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'GET',
      headers,
    });
  }

  async post<T>(
    endpoint: string,
    data?: unknown,
    headers?: Record<string, string>
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
      headers,
    });
  }

  async put<T>(
    endpoint: string,
    data?: unknown,
    headers?: Record<string, string>
  ): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
      headers,
    });
  }

  async delete<T>(endpoint: string, headers?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
      headers,
    });
  }
}

// Instancia global del cliente API
export const apiClient = new ApiClient();

// Funciones helper para endpoints específicos
export const api = {
  // Mesas
  mesas: {
    getAll: () => apiClient.get(API_CONFIG.ENDPOINTS.MESAS),
    getById: (id: number) => apiClient.get(API_CONFIG.ENDPOINTS.MESA_BY_ID(id)),
    create: (data: MesaCreate) => apiClient.post(API_CONFIG.ENDPOINTS.MESA_CREATE, data),
    update: (id: number, data: MesaUpdate) => apiClient.put(API_CONFIG.ENDPOINTS.MESA_UPDATE(id), data),
    delete: (id: number) => apiClient.delete(API_CONFIG.ENDPOINTS.MESA_DELETE(id)),
    merge: (sourceMesaIds: number[], targetMesaId: number) => apiClient.post(API_CONFIG.ENDPOINTS.MESA_MERGE, { 'source_mes-ids': sourceMesaIds, 'target_mes-id': targetMesaId }),
  },

  // Consumos
  consumos: {
    getAbiertosByMesa: (mesaId: number) => apiClient.get(API_CONFIG.ENDPOINTS.CONSUMOS_ABIERTOS(mesaId)),
    create: (data: ConsumoCreate) => apiClient.post(API_CONFIG.ENDPOINTS.CONSUMO_CREATE, data),
    addDetalle: (consumoId: number, data: ConsumoDetalleCreate) => apiClient.post(API_CONFIG.ENDPOINTS.CONSUMO_ADD_DETALLE(consumoId), data),
    cerrar: (consumoId: number, porcentajePropina: number = 0) => apiClient.put(API_CONFIG.ENDPOINTS.CONSUMO_CERRAR(consumoId), { porcentaje_propina: porcentajePropina }),
    facturar: (consumoId: number, metodoPago: string = 'Efectivo', cobrarPropina: boolean = true) => apiClient.put(API_CONFIG.ENDPOINTS.CONSUMO_FACTURAR(consumoId), { metodo_pago: metodoPago, cobrar_propina: cobrarPropina }),
    getAllActiveByEmpresa: (empresaId: number) => apiClient.get(`${API_CONFIG.ENDPOINTS.CONSUMOS_GET_ALL_ACTIVE_BY_EMPRESA}?empres-id=${empresaId}`),
  },

  // Tickets
  tickets: {
    generar: (data: TicketRequest) => apiClient.post(API_CONFIG.ENDPOINTS.TICKET_GENERAR, data),
  },

  // Comandas
  comandas: {
    getPendientes: () => apiClient.get(API_CONFIG.ENDPOINTS.COMANDAS_PENDIENTES),
    marcarImpreso: (ids: number[]) => apiClient.post(API_CONFIG.ENDPOINTS.COMANDAS_MARCAR_IMPRESO, { ids_detalles: ids }),
  },

  // Cocina
  cocina: {
    getItems: () => apiClient.get<ConsumoMesaDetallePopulated[]>(API_CONFIG.ENDPOINTS.COCINA_ITEMS),
    updateEstado: (id: number, nuevoEstado: string) => apiClient.put<ConsumoMesaDetallePopulated>(API_CONFIG.ENDPOINTS.COCINA_UPDATE_ESTADO(id), { nuevo_estado: nuevoEstado }),
  },

  // Comprobantes
  comprobantes: {
    generarPDF: async (payload: any) => apiClient.download(API_CONFIG.ENDPOINTS.COMPROBANTES_GENERAR, payload),
    agrupar: (ids: number[], nuevoTipo: string) => apiClient.post(API_CONFIG.ENDPOINTS.COMPROBANTES_AGRUPAR, { ids_comprobantes: ids, nuevo_tipo_comprobante: nuevoTipo }),
    facturarLote: (idsMovimientos: number[], idClienteFinal?: number) => apiClient.post(API_CONFIG.ENDPOINTS.COMPROBANTES_FACTURAR_LOTE, { ids_movimientos: idsMovimientos, id_cliente_final: idClienteFinal }),
  },

  impresion: {
    generarComandaPDF: async (payload: any) => apiClient.download(API_CONFIG.ENDPOINTS.IMPRESION_COMANDA_PDF, payload),
    generarMesaPDF: async (consumoId: number) => apiClient.download(API_CONFIG.ENDPOINTS.IMPRESION_MESA_PDF, { id_consumo_mesa: consumoId }),
    abrirSesion: () => apiClient.post(API_CONFIG.ENDPOINTS.IMPRESION_COMANDA_PDF.replace('/comanda/pdf', '/sesion/abrir')),
    cerrarSesion: () => apiClient.post(API_CONFIG.ENDPOINTS.IMPRESION_COMANDA_PDF.replace('/comanda/pdf', '/sesion/cerrar')),
  },

  // Articulos
  articulos: {
    getAll: (empresaId: number) => apiClient.get(`${API_CONFIG.ENDPOINTS.PRODUCTOS}?empres-id=${empresaId}`),
    getById: (id: number) => apiClient.get(API_CONFIG.ENDPOINTS.ARTICULO_BY_ID(id)),
    buscar: (termino: string, limit: number = 20, skip: number = 0) =>
      apiClient.get(`${API_CONFIG.ENDPOINTS.ARTICULOS_BUSCAR}?termino=${encodeURIComponent(termino)}&limit=${limit}&skip=${skip}`),
  },

  // Caja
  caja: {
    getEstado: () => apiClient.get(API_CONFIG.ENDPOINTS.CAJA_ESTADO),
  },
};
