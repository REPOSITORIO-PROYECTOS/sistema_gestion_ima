export type PrecioVigente = {
  precio_venta: number;
  venta_negocio: number | null;
  precio_manual: boolean;
};

type CatalogoVigente = {
  idEmpresa: number;
  porId: Map<string, PrecioVigente>;
};

let vigente: CatalogoVigente | null = null;

type ArticuloPublicable = {
  id: number | string;
  precio_venta: number;
  venta_negocio?: number | null;
  precio_manual?: boolean;
};

/** Precios de la última bajada completa. La búsqueda los pisa sobre respuestas viejas. */
export function publicarCatalogoVigente(
  idEmpresa: number,
  articulos: ArticuloPublicable[],
): void {
  const porId = new Map<string, PrecioVigente>();
  for (const articulo of articulos) {
    const venta = Number(articulo.precio_venta);
    const negocio = articulo.venta_negocio;
    porId.set(String(articulo.id), {
      precio_venta: Number.isFinite(venta) ? venta : 0,
      venta_negocio:
        negocio === null || negocio === undefined || !Number.isFinite(Number(negocio))
          ? null
          : Number(negocio),
      precio_manual: Boolean(articulo.precio_manual),
    });
  }
  vigente = { idEmpresa, porId };
}

export function precioVigenteDe(
  idEmpresa: number,
  id: string,
): PrecioVigente | undefined {
  if (!vigente || vigente.idEmpresa !== idEmpresa) return undefined;
  return vigente.porId.get(id);
}

export function limpiarCatalogoVigente(): void {
  vigente = null;
}

type ProductoConPrecio = {
  id: string;
  precio_venta: number;
  venta_negocio: number;
  precio_manual?: boolean;
};

export function aplicarPreciosVigentesABusqueda<T extends ProductoConPrecio>(
  idEmpresa: number,
  productos: T[],
): T[] {
  return productos.map((producto) => {
    const precio = precioVigenteDe(idEmpresa, producto.id);
    if (!precio) return producto;
    return {
      ...producto,
      precio_venta: precio.precio_venta,
      venta_negocio: precio.venta_negocio ?? producto.venta_negocio,
      precio_manual: precio.precio_manual,
    };
  });
}
