import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface FacturacionStore {
  habilitarExtras: boolean;
  toggleExtras: () => void;
  setHabilitarExtras: (val: boolean) => void;

  recargoTransferenciaActivo: boolean;
  toggleRecargoTransferencia: () => void;
  recargoTransferencia: number;
  setRecargoTransferencia: (val: number) => void;

  recargoBancarioActivo: boolean;
  toggleRecargoBancario: () => void;
  recargoBancario: number;
  setRecargoBancario: (val: number) => void;

  /** NUEVO: formato de comprobante */
  formatoComprobante: string;
  setFormatoComprobante: (val: string) => void;
}

export const useFacturacionStore = create<FacturacionStore>()(
  persist(
    (set) => ({
      habilitarExtras: false,
      toggleExtras: () =>
        set((state) => ({ habilitarExtras: !state.habilitarExtras })),
      setHabilitarExtras: (val) => set({ habilitarExtras: val }),

      recargoTransferenciaActivo: false,
      toggleRecargoTransferencia: () =>
        set((state) => ({ recargoTransferenciaActivo: !state.recargoTransferenciaActivo })),
      recargoTransferencia: 0,
      setRecargoTransferencia: (val) => set({ recargoTransferencia: val }),

      recargoBancarioActivo: false,
      toggleRecargoBancario: () =>
        set((state) => ({ recargoBancarioActivo: !state.recargoBancarioActivo })),
      recargoBancario: 0,
      setRecargoBancario: (val) => set({ recargoBancario: val }),

      formatoComprobante: "ticket", 
      setFormatoComprobante: (val) => set({ formatoComprobante: val }),

    }),
    {
      name: 'facturacion-storage',
    }
  )
);