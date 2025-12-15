import { create } from 'zustand';
import type { Articulo } from '@/lib/types/mesas';

interface ProductosState {
  productos: Articulo[];
  loading: boolean;
  error: string | null;

  // Actions
  fetchProductos: () => Promise<void>;
  getProductoById: (id: number) => Articulo | undefined;
}

export const useProductosStore = create<ProductosState>((set, get) => ({
  productos: [],
  loading: false,
  error: null,

  fetchProductos: async () => {
    set({ loading: true });
    try {
      // TODO: Implementar endpoint de productos en el backend
      // const response = await api.productos.getAll();
      // set({ productos: response.data });

      // Por ahora, datos mock
      const mockProductos: Articulo[] = [
        { id: 1, descripcion: 'Hamburguesa Clásica', precio_venta: 1500, stock_actual: 50, activo: true },
        { id: 2, descripcion: 'Pizza Margherita', precio_venta: 2200, stock_actual: 30, activo: true },
        { id: 3, descripcion: 'Coca Cola 500ml', precio_venta: 300, stock_actual: 100, activo: true },
        { id: 4, descripcion: 'Café Expresso', precio_venta: 250, stock_actual: 80, activo: true },
        { id: 5, descripcion: 'Ensalada César', precio_venta: 1200, stock_actual: 25, activo: true },
        { id: 6, descripcion: 'Milanesa con Papas', precio_venta: 1800, stock_actual: 40, activo: true },
        { id: 7, descripcion: 'Agua Mineral 500ml', precio_venta: 200, stock_actual: 150, activo: true },
        { id: 8, descripcion: 'Cerveza Quilmes 1L', precio_venta: 450, stock_actual: 60, activo: true },
        { id: 9, descripcion: 'Tiramisú', precio_venta: 800, stock_actual: 20, activo: true },
        { id: 10, descripcion: 'Flan con Dulce de Leche', precio_venta: 600, stock_actual: 30, activo: true },
      ];

      set({ productos: mockProductos });
    } catch (error) {
      // TODO: Implementar manejo de errores
      console.error('Error al cargar productos:', error);
    } finally {
      set({ loading: false });
    }
  },

  getProductoById: (id: number) => {
    return get().productos.find(p => p.id === id);
  },
}));