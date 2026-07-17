import { create } from 'zustand'
import { API_CONFIG } from '@/lib/api-config'
import { getOfflineMeta, upsertOfflineMeta } from '@/lib/offline/db'
// Ya no necesitamos 'persist', lo eliminamos de las importaciones.

// Definimos la 'forma' de la respuesta que esperamos de nuestro nuevo endpoint de verificación
interface EstadoCajaAPI {
  caja_abierta: boolean;
  id_sesion?: number;
  fecha_apertura?: string;
}

type CajaOfflineOptions = {
  idEmpresa?: number;
  usarCacheDegradado?: boolean;
  idSesion?: number | null;
};

// Ampliamos la interfaz de nuestro store
interface CajaStore {
  cajaAbierta: boolean;
  idSesion: number | null;
  modoOfflineCaja: boolean;
  // Añadimos un estado para saber si ya se verificó con el backend
  estadoVerificado: boolean;
  // --- ACCIÓN NUEVA Y CLAVE ---
  verificarEstadoCaja: (token: string, options?: CajaOfflineOptions) => Promise<void>;
  setCajaAbierta: (valor: boolean, options?: CajaOfflineOptions) => void;
  clearCaja: (options?: CajaOfflineOptions) => void;
}

export const useCajaStore = create<CajaStore>()((set) => ({
  // El estado inicial es siempre 'false' y 'no verificado'
  cajaAbierta: false,
  idSesion: null,
  modoOfflineCaja: false,
  estadoVerificado: false,

  // Esta función se llamará cada vez que la aplicación cargue
  verificarEstadoCaja: async (token, options) => {
    if (!token) {
      set({ cajaAbierta: false, idSesion: null, modoOfflineCaja: false, estadoVerificado: true });
      return;
    }

    const usarSesionCacheada = async () => {
      if (!options?.usarCacheDegradado || !options.idEmpresa) {
        set({ cajaAbierta: false, idSesion: null, modoOfflineCaja: false, estadoVerificado: true });
        return;
      }

      const meta = await getOfflineMeta(options.idEmpresa);
      if (meta?.id_sesion_caja) {
        set({
          cajaAbierta: true,
          idSesion: meta.id_sesion_caja,
          modoOfflineCaja: true,
          estadoVerificado: true,
        });
        return;
      }

      set({ cajaAbierta: false, idSesion: null, modoOfflineCaja: false, estadoVerificado: true });
    };

    try {
      // Llamamos a nuestro nuevo endpoint de verificación en el backend
      const res = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CAJA_ESTADO}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        await usarSesionCacheada();
        return;
      }
      const data: EstadoCajaAPI = await res.json();
      const idSesion = data.caja_abierta ? data.id_sesion ?? null : null;

      if (options?.usarCacheDegradado && options.idEmpresa) {
        await upsertOfflineMeta(options.idEmpresa, { id_sesion_caja: idSesion });
      }
      
      // Actualizamos nuestro estado con la respuesta REAL del backend
      set({
        cajaAbierta: data.caja_abierta,
        idSesion,
        modoOfflineCaja: false,
        estadoVerificado: true,
      });

    } catch (error) {
      console.error("Error al verificar estado de la caja:", error);
      await usarSesionCacheada();
    }
  },

  // Esta función se sigue usando cuando abres la caja manualmente
  setCajaAbierta: (valor, options) => {
    const idSesion = valor ? options?.idSesion ?? null : null;
    if (options?.usarCacheDegradado && options.idEmpresa) {
      void upsertOfflineMeta(options.idEmpresa, { id_sesion_caja: idSesion });
    }
    set({ cajaAbierta: valor, idSesion, modoOfflineCaja: false, estadoVerificado: true });
  },
  
  // Esta función se sigue usando cuando cierras la caja manualmente
  clearCaja: (options) => {
    if (options?.usarCacheDegradado && options.idEmpresa) {
      void upsertOfflineMeta(options.idEmpresa, { id_sesion_caja: null });
    }
    set({ cajaAbierta: false, idSesion: null, modoOfflineCaja: false, estadoVerificado: true });
  },
}));