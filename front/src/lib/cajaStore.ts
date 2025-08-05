// stores/cajaStore.ts
import { create } from 'zustand';
// Ya no necesitamos 'persist', lo eliminamos de las importaciones.

// Definimos la 'forma' de la respuesta que esperamos de nuestro nuevo endpoint de verificación
interface EstadoCajaAPI {
  caja_abierta: boolean;
  id_sesion?: number;
  fecha_apertura?: string;
}

// Ampliamos la interfaz de nuestro store
interface CajaStore {
  cajaAbierta: boolean;
  // Añadimos un estado para saber si ya se verificó con el backend
  estadoVerificado: boolean;
  // --- ACCIÓN NUEVA Y CLAVE ---
  verificarEstadoCaja: (token: string) => Promise<void>;
  setCajaAbierta: (valor: boolean) => void;
  clearCaja: () => void;
}

export const useCajaStore = create<CajaStore>()((set) => ({
  // El estado inicial es siempre 'false' y 'no verificado'
  cajaAbierta: false,
  estadoVerificado: false,

  // Esta función se llamará cada vez que la aplicación cargue
  verificarEstadoCaja: async (token) => {
    if (!token) {
      set({ cajaAbierta: false, estadoVerificado: true });
      return;
    }
    try {
      // Llamamos a nuestro nuevo endpoint de verificación en el backend
      const res = await fetch("https://sistema-ima.sistemataup.online/api/caja/estado-actual", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        // Si hay un error en la API, por seguridad asumimos que la caja está cerrada
        set({ cajaAbierta: false, estadoVerificado: true });
        return;
      }
      const data: EstadoCajaAPI = await res.json();
      
      // Actualizamos nuestro estado con la respuesta REAL del backend
      set({ cajaAbierta: data.caja_abierta, estadoVerificado: true });

    } catch (error) {
      console.error("Error al verificar estado de la caja:", error);
      // En caso de error de red, también asumimos que la caja está cerrada
      set({ cajaAbierta: false, estadoVerificado: true });
    }
  },

  // Esta función se sigue usando cuando abres la caja manualmente
  setCajaAbierta: (valor) => set({ cajaAbierta: valor, estadoVerificado: true }),
  
  // Esta función se sigue usando cuando cierras la caja manualmente
  clearCaja: () => set({ cajaAbierta: false, estadoVerificado: true }),
}));