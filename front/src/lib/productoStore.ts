import { create } from "zustand";
import { persist } from "zustand/middleware";

// Tipado unificado
export type Producto = {
  id: string;
  nombre: string; // Lo usamos siempre así en frontend
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
};

type ProductoStore = {
  productos: Producto[];
  setProductos: (productos: Producto[]) => void;
  clearProductos: () => void;
};

export const useProductoStore = create(
  persist<ProductoStore>(
    (set) => ({
      productos: [],
      setProductos: (productos) => set({ productos }),
      clearProductos: () => set({ productos: [] }),
    }),
    {
      name: "producto-storage", // clave en localStorage
    }
  )
);