import { create } from 'zustand';
import { api } from '@/lib/api-client';
import type {
  Mesa,
  MesaLog,
  ConsumoMesa,
  MesaCreate,
  MesaUpdate,
  ConsumoCreate,
  ConsumoDetalleCreate,
  TicketRequest,
  TicketResponse
} from '@/lib/types/mesas';

interface MesasStore {
  // Estado
  mesas: Mesa[];
  mesaLogs: MesaLog[];
  consumos: ConsumoMesa[];
  loading: boolean;
  error: string | null;

  // Acciones para Mesas
  fetchMesas: () => Promise<void>;
  createMesa: (data: MesaCreate) => Promise<boolean>;
  updateMesa: (id: number, data: MesaUpdate) => Promise<boolean>;
  deleteMesa: (id: number) => Promise<boolean>;

  // Acciones para Logs
  fetchMesaLogs: () => Promise<void>;

  // Acciones para Consumos
  fetchConsumos: () => Promise<void>;
  createConsumo: (data: ConsumoCreate) => Promise<ConsumoMesa | null>;
  addDetalleConsumo: (idConsumo: number, data: ConsumoDetalleCreate) => Promise<boolean>;
  cerrarConsumo: (idConsumo: number) => Promise<boolean>;
  facturarConsumo: (idConsumo: number) => Promise<boolean>;

  // Acciones para Tickets
  generarTicket: (data: TicketRequest) => Promise<TicketResponse | null>;

  // Utilidades
  clearError: () => void;
}

export const useMesasStore = create<MesasStore>((set, get) => ({
  // Estado inicial
  mesas: [],
  mesaLogs: [],
  consumos: [],
  loading: false,
  error: null,

  // Mesas
  fetchMesas: async () => {
    set({ loading: true, error: null });
    try {
      const response = await api.mesas.getAll();
      if (response.success && response.data) {
        set({ mesas: response.data as Mesa[], loading: false });
      } else {
        set({ error: response.error || 'Error al cargar mesas', loading: false });
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
    }
  },

  createMesa: async (data: MesaCreate) => {
    set({ loading: true, error: null });
    try {
      const response = await api.mesas.create(data);
      if (response.success) {
        // Recargar mesas después de crear
        await get().fetchMesas();
        set({ loading: false });
        return true;
      } else {
        // Detectar errores específicos de duplicado
        const errorMessage = response.error || 'Error al crear mesa';
        let processedError = errorMessage;

        if (errorMessage.includes('Duplicate entry') || errorMessage.includes('uq_numero_empresa_mesa')) {
          processedError = 'Ya existe una mesa con este número. Por favor elige un número diferente.';
        } else if (errorMessage.includes('1062')) {
          processedError = 'Ya existe una mesa con este número. Por favor elige un número diferente.';
        }

        set({ error: processedError, loading: false });
        return false;
      }
    } catch (error) {
      let errorMessage = 'Error desconocido';
      if (error instanceof Error) {
        errorMessage = error.message;
        // Detectar errores específicos de duplicado en la respuesta HTTP
        if (errorMessage.includes('Duplicate entry') || errorMessage.includes('uq_numero_empresa_mesa') || errorMessage.includes('1062')) {
          errorMessage = 'Ya existe una mesa con este número. Por favor elige un número diferente.';
        }
      }
      set({ error: errorMessage, loading: false });
      return false;
    }
  },

  updateMesa: async (id: number, data: MesaUpdate) => {
    set({ loading: true, error: null });
    try {
      const response = await api.mesas.update(id, data);
      if (response.success) {
        // Recargar mesas después de actualizar
        await get().fetchMesas();
        set({ loading: false });
        return true;
      } else {
        set({ error: response.error || 'Error al actualizar mesa', loading: false });
        return false;
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
      return false;
    }
  },

  deleteMesa: async (id: number) => {
    set({ loading: true, error: null });
    try {
      const response = await api.mesas.delete(id);
      if (response.success) {
        // Recargar mesas después de eliminar
        await get().fetchMesas();
        set({ loading: false });
        return true;
      } else {
        set({ error: response.error || 'Error al eliminar mesa', loading: false });
        return false;
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
      return false;
    }
  },

  // Logs de Mesas
  fetchMesaLogs: async () => {
    set({ loading: true, error: null });
    try {
      // TODO: Implementar endpoint en el backend para obtener logs
      // const response = await api.mesas.getLogs();
      // if (response.success && response.data) {
      //   set({ mesaLogs: response.data as MesaLog[], loading: false });
      // } else {
      //   set({ error: response.error || 'Error al cargar logs de mesas', loading: false });
      // }

      // Por ahora, simulamos logs vacíos
      set({ mesaLogs: [], loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
    }
  },

  // Consumos
  fetchConsumos: async () => {
    set({ loading: true, error: null });
    try {
      const mesas = get().mesas;
      if (mesas.length === 0) {
        await get().fetchMesas();
      }
      const ids = get().mesas.map(m => m.id);
      const results = await Promise.all(ids.map(id => api.consumos.getAbiertosByMesa(id)));
      const agregados: ConsumoMesa[] = [];
      results.forEach(r => {
        if (r.success && r.data) {
          const lista = (r.data as ConsumoMesa[]).map(c => ({
            ...c,
            estado: (typeof c.estado === 'string' ? c.estado.toLowerCase() : c.estado) as ConsumoMesa['estado'],
          }));
          agregados.push(...lista);
        }
      });
      set({ consumos: agregados, loading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
    }
  },

  createConsumo: async (data: ConsumoCreate) => {
    set({ loading: true, error: null });
    try {
      const response = await api.consumos.create(data);
      if (response.success && response.data) {
        // Recargar consumos
        await get().fetchConsumos();
        set({ loading: false });
        return response.data as ConsumoMesa;
      } else {
        set({ error: response.error || 'Error al crear consumo', loading: false });
        return null;
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
      return null;
    }
  },

  addDetalleConsumo: async (idConsumo: number, data: ConsumoDetalleCreate) => {
    set({ loading: true, error: null });
    try {
      const response = await api.consumos.addDetalle(idConsumo, data);
      if (response.success) {
        // Recargar consumos para actualizar detalles
        await get().fetchConsumos();
        set({ loading: false });
        return true;
      } else {
        set({ error: response.error || 'Error al agregar detalle', loading: false });
        return false;
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
      return false;
    }
  },

  cerrarConsumo: async (idConsumo: number) => {
    set({ loading: true, error: null });
    try {
      const response = await api.consumos.cerrar(idConsumo);
      if (response.success) {
        await get().fetchConsumos();
        set({ loading: false });
        return true;
      } else {
        set({ error: response.error || 'Error al cerrar consumo', loading: false });
        return false;
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
      return false;
    }
  },

  facturarConsumo: async (idConsumo: number) => {
    set({ loading: true, error: null });
    try {
      const response = await api.consumos.facturar(idConsumo);
      if (response.success) {
        await get().fetchConsumos();
        set({ loading: false });
        return true;
      } else {
        set({ error: response.error || 'Error al facturar consumo', loading: false });
        return false;
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
      return false;
    }
  },

  // Tickets
  generarTicket: async (data: TicketRequest) => {
    set({ loading: true, error: null });
    try {
      const response = await api.tickets.generar({ ...data, formato: data.formato ?? 'ticket' });
      if (response.success && response.data) {
        set({ loading: false });
        return response.data as TicketResponse;
      } else {
        set({ error: response.error || 'Error al generar ticket', loading: false });
        return null;
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
      return null;
    }
  },

  // Utilidades
  clearError: () => set({ error: null }),
}));
