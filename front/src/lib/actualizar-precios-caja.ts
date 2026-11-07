export type LineaCaja = {
  id?: string;
  tipo: string;
  cantidad: number;
  precioTotal: number;
  precioBase: number;
  descuentoAplicado?: boolean;
  porcentajeDescuento?: number;
  descuentoNominal?: number;
};

export type ArticuloPrecio = {
  precio_venta: number;
  venta_negocio?: number | null;
  precio_manual?: boolean;
};

function redondear(valor: number): number {
  return Math.round(valor * 100) / 100;
}

/** Cliente final usa precio de venta. Cliente registrado usa precio de negocio. */
export function precioSegunCliente(
  articulo: ArticuloPrecio,
  tipoClienteId: string,
): number {
  const venta = Number(articulo.precio_venta);
  const ventaOk = Number.isFinite(venta) ? venta : 0;
  if (tipoClienteId === "0") return ventaOk;
  if (articulo.venta_negocio === null || articulo.venta_negocio === undefined) {
    return ventaOk;
  }
  const negocio = Number(articulo.venta_negocio);
  return Number.isFinite(negocio) ? negocio : ventaOk;
}

/** Reescribe base y total de la línea. No toca cantidad ni descuentos cargados. */
export function aplicarPrecioVigente(
  linea: LineaCaja,
  articulo: ArticuloPrecio | null,
  tipoClienteId: string,
): LineaCaja {
  if (!articulo || articulo.precio_manual) return linea;

  const unitario = precioSegunCliente(articulo, tipoClienteId);
  const precioBase = redondear(unitario * linea.cantidad);
  const descPorc = linea.porcentajeDescuento || 0;
  const descNom = linea.descuentoNominal || 0;
  const subtotal = precioBase * (1 - descPorc / 100);
  const precioTotal = Math.max(0, redondear(subtotal - descNom));

  return {
    ...linea,
    precioBase,
    precioTotal,
    descuentoAplicado: descPorc > 0 || descNom > 0,
  };
}
