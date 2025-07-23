import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface FacturacionStore {
  habilitarExtras: boolean;
  toggleExtras: () => void;
  setHabilitarExtras: (val: boolean) => void;
}

export const useFacturacionStore = create<FacturacionStore>()(
  persist(
    (set) => ({
      habilitarExtras: false,
      toggleExtras: () =>
        set((state) => ({ habilitarExtras: !state.habilitarExtras })),
      setHabilitarExtras: (val) => set({ habilitarExtras: val }),
    }),
    {
      name: 'facturacion-storage', 
    }
  )
);