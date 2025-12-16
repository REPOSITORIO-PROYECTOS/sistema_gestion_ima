import { create } from 'zustand';
import { toast } from 'sonner';
import { api } from '@/lib/api-client';
import { useAuthStore } from '@/lib/authStore';
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
  unirMesas: (ids: number[]) => Promise<boolean>;

  // Acciones para Logs
  fetchMesaLogs: () => Promise<void>;

  // Acciones para Consumos
  fetchConsumos: () => Promise<void>;
  createConsumo: (data: ConsumoCreate) => Promise<ConsumoMesa | null>;
  addDetalleConsumo: (idConsumo: number, data: ConsumoDetalleCreate) => Promise<{ ok: boolean; error?: string }>;
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
        toast.error(processedError); // Add toast notification
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
      toast.error(errorMessage); // Add toast notification
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

  unirMesas: async (ids: number[]) => {
    set({ loading: true, error: null });
    try {
      // Asumimos que tienes este endpoint en tu backend
      const response = await api.mesas.merge(ids, ids[0]);
      if (response.success) {
        await get().fetchMesas(); // Recargar estado de mesas
        await get().fetchConsumos(); // Recargar consumos unificados
        set({ loading: false });
        return true;
      } else {
        set({ error: response.error || 'Error al unir mesas', loading: false });
        return false;
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Error de conexión', loading: false });
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
      toast.error(error instanceof Error ? error.message : 'Error desconocido');
    }
  },

  // Consumos
  fetchConsumos: async () => {
    set({ loading: true, error: null });
    try {
      const { usuario } = useAuthStore.getState();
      if (!usuario?.id_empresa) {
        set({ error: 'ID de empresa no disponible', loading: false });
        toast.error('ID de empresa no disponible para cargar consumos.');
        return;
      }
      const mesasRes = await api.mesas.getAll();
      if (!mesasRes.success || !mesasRes.data) {
        set({ error: mesasRes.error || 'Error al cargar mesas para consumos', loading: false });
        return;
      }
      const mesas = mesasRes.data as Mesa[];
      const consumosPorMesaRes = await Promise.all(
        mesas.map((m) => api.consumos.getAbiertosByMesa(m.id))
      );
      const acumulados: ConsumoMesa[] = [];
      for (const r of consumosPorMesaRes) {
        if (r.success && Array.isArray(r.data)) {
          acumulados.push(
            ...((r.data as ConsumoMesa[]).map(c => ({
              ...c,
              estado: (typeof c.estado === 'string' ? c.estado.toLowerCase() : c.estado) as ConsumoMesa['estado'],
            })))
          );
        }
      }
      set({ consumos: acumulados, loading: false });
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
        return { ok: true };
      } else {
        set({ error: response.error || 'Error al agregar detalle', loading: false });
        return { ok: false, error: response.error };
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Error desconocido',
        loading: false
      });
      return { ok: false, error: error instanceof Error ? error.message : 'Error desconocido' };
    }
  },

  cerrarConsumo: async (idConsumo: number) => {
    set({ loading: true, error: null });
    try {
      const response = await api.consumos.cerrar(idConsumo);
      if (response.success) {
        const consumo = get().consumos.find(c => c.id === idConsumo);
        if (consumo?.id_mesa) {
          await get().updateMesa(consumo.id_mesa, { estado: 'LIBRE' });
        }
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
        const consumo = get().consumos.find(c => c.id === idConsumo);
        if (consumo?.id_mesa) {
          await get().updateMesa(consumo.id_mesa, { estado: 'LIBRE' });
        }
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
