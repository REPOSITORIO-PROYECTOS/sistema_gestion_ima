import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface Empresa {
  id_empresa: number;
  nombre_negocio?: string;
  cuit?: string;
  color_principal: string;
  ruta_logo?: string;
  ruta_icono?: string;
  afip_condicion_iva?: string;
  afip_punto_venta_predeterminado?: number;
  direccion_negocio?: string;
  telefono_negocio?: string;
  mail_negocio?: string;
  link_google_sheets?: string;
  aclaraciones_legales?: Record<string, string>;
}

interface EmpresaStore {
  empresa: Empresa | null;
  setEmpresa: (empresa: Empresa) => void;
  clearEmpresa: () => void;
}

export const useEmpresaStore = create<EmpresaStore>()(
  persist(
    (set) => ({
      empresa: null,
      setEmpresa: (empresa) => set({ empresa }),
      clearEmpresa: () => set({ empresa: null }),
    }),
    {
      name: 'empresa-storage',
      storage: createJSONStorage(() => sessionStorage),
    }
  )
);
