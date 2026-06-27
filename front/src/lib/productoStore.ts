import { create } from "zustand";

export type Producto = {
  id: string;
  nombre: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
  unidad_venta: string;
  precio_manual?: boolean;
};

const MAX_CACHE = 100;

type ProductoStore = {
  /** Cache en memoria de productos usados recientemente (no es el catálogo completo). */
  productos: Producto[];
  upsertProductos: (nuevos: Producto[]) => void;
  getProductoById: (id: string) => Producto | undefined;
  /** @deprecated Usar upsertProductos. Mantenido por compatibilidad. */
  setProductos: (productos: Producto[]) => void;
  clearProductos: () => void;
};

export const useProductoStore = create<ProductoStore>((set, get) => ({
  productos: [],

  upsertProductos: (nuevos) =>
    set((state) => {
      const map = new Map(state.productos.map((p) => [p.id, p]));
      for (const p of nuevos) {
        map.set(p.id, p);
      }
      const merged = Array.from(map.values());
      return { productos: merged.slice(-MAX_CACHE) };
    }),

  getProductoById: (id) => get().productos.find((p) => p.id === id),

  setProductos: (productos) => set({ productos: productos.slice(-MAX_CACHE) }),

  clearProductos: () => set({ productos: [] }),
}));
