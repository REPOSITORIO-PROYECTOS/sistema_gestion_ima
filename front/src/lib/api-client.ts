import { API_CONFIG, ApiResponse, getAuthHeaders } from './api-config';
import type {
  MesaCreate,
  MesaUpdate,
  ConsumoCreate,
  ConsumoDetalleCreate,
  TicketRequest
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
    cerrar: (consumoId: number) => apiClient.put(API_CONFIG.ENDPOINTS.CONSUMO_CERRAR(consumoId)),
    facturar: (consumoId: number) => apiClient.put(API_CONFIG.ENDPOINTS.CONSUMO_FACTURAR(consumoId)),
    getAllActiveByEmpresa: (empresaId: number) => apiClient.get(`${API_CONFIG.ENDPOINTS.CONSUMOS_GET_ALL_ACTIVE_BY_EMPRESA}?empres-id=${empresaId}`),
  },

  // Tickets
  tickets: {
    generar: (data: TicketRequest) => apiClient.post(API_CONFIG.ENDPOINTS.TICKET_GENERAR, data),
  },

  // Articulos
  articulos: {
    getAll: (empresaId: number) => apiClient.get(`${API_CONFIG.ENDPOINTS.PRODUCTOS}?empres-id=${empresaId}`),
    getById: (id: number) => apiClient.get(API_CONFIG.ENDPOINTS.ARTICULO_BY_ID(id)),
  },

  // Caja
  caja: {
    getEstado: () => apiClient.get(API_CONFIG.ENDPOINTS.CAJA_ESTADO),
  },
};
