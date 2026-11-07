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

export type AplicarPrecioOptions = {
  /** Al tocar «Actualizar precios», también pisa líneas de precio manual. */
  forzarManual?: boolean;
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

/** Reescribe base y total de la línea. Conserva cantidad y descuentos cargados. */
export function aplicarPrecioVigente(
  linea: LineaCaja,
  articulo: ArticuloPrecio | null,
  tipoClienteId: string,
  options: AplicarPrecioOptions = {},
): LineaCaja {
  if (!articulo) return linea;
  if (articulo.precio_manual && !options.forzarManual) return linea;

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

/** Aplica el precio vigente a todas las líneas posibles del resumen. */
export function actualizarTodasLasLineas(
  lineas: LineaCaja[],
  preciosPorId: Map<string, ArticuloPrecio>,
  tipoClienteId: string,
): { lineas: LineaCaja[]; actualizadas: number; sinPrecio: number } {
  let actualizadas = 0;
  let sinPrecio = 0;

  const siguientes = lineas.map((linea) => {
    if (!linea.id) {
      sinPrecio += 1;
      return linea;
    }
    const articulo = preciosPorId.get(linea.id);
    if (!articulo) {
      sinPrecio += 1;
      return linea;
    }
    const recalculada = aplicarPrecioVigente(linea, articulo, tipoClienteId, {
      forzarManual: true,
    });
    if (
      recalculada.precioBase !== linea.precioBase
      || recalculada.precioTotal !== linea.precioTotal
    ) {
      actualizadas += 1;
    }
    return recalculada;
  });

  return { lineas: siguientes, actualizadas, sinPrecio };
}
