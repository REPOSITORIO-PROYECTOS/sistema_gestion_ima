// stores/useMovimientosCajaStore.ts
import { create } from 'zustand';

// Definimos el tipo aquí mismo para no necesitar el archivo de tipos
type FiltroTipo = "TODOS" | "PENDIENTES" | "FACTURADOS" | "INGRESOS" | "EGRESOS";

interface MovimientosCajaState {
  filtroActual: FiltroTipo;
  seleccionados: number[];
  setFiltro: (filtro: FiltroTipo) => void;
  toggleSeleccion: (id: number) => void;
  resetSeleccion: () => void;
}

export const useMovimientosCajaStore = create<MovimientosCajaState>((set) => ({
  filtroActual: "TODOS",
  seleccionados: [],
  setFiltro: (filtro) => set({ filtroActual: filtro, seleccionados: [] }),
  toggleSeleccion: (id) => {
    set((state) => ({
      seleccionados: state.seleccionados.includes(id)
        ? state.seleccionados.filter((selId) => selId !== id)
        : [...state.seleccionados, id],
    }));
  },
  resetSeleccion: () => set({ seleccionados: [] }),
}));