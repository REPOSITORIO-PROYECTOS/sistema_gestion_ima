import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface FacturacionStore {
  habilitarExtras: boolean;
  toggleExtras: () => void;
  setHabilitarExtras: (val: boolean) => void;

  // Nuevo estado para recargos
  recargoActivo: boolean;
  toggleRecargo: () => void;
  recargoTransferencia: number;
  setRecargoTransferencia: (val: number) => void;
}

export const useFacturacionStore = create<FacturacionStore>()(
  persist(
    (set) => ({
      habilitarExtras: false,
      toggleExtras: () =>
        set((state) => ({ habilitarExtras: !state.habilitarExtras })),
      setHabilitarExtras: (val) => set({ habilitarExtras: val }),

      recargoActivo: false,
      toggleRecargo: () =>
        set((state) => ({ recargoActivo: !state.recargoActivo })),
      recargoTransferencia: 0,
      setRecargoTransferencia: (val) => set({ recargoTransferencia: val }),
    }),
    {
      name: 'facturacion-storage',
    }
  )
);