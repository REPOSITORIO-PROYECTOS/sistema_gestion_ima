export type ArticuloIngreso = {
  id: number;
  codigo_interno: string;
  descripcion: string;
  stock_actual: number;
  precio_venta: number;
  venta_negocio?: number | null;
  barcodes?: string[];
};

export function textoStock(stock: number): string {
  const valor = Number.isFinite(stock) ? stock : 0;
  return `stk ${valor}`;
}

export function textoBarras(barcodes: string[] | undefined): string {
  return (barcodes ?? []).map((codigo) => codigo.trim()).filter(Boolean).join(", ");
}

export function parseBarras(valor: string): string[] {
  const vistos = new Set<string>();
  const barras: string[] = [];
  for (const parte of valor.split(/[,;|]/)) {
    const codigo = parte.trim();
    if (!codigo || vistos.has(codigo)) continue;
    vistos.add(codigo);
    barras.push(codigo);
  }
  return barras;
}

function numeroPrecio(valor: string): number | undefined {
  const limpio = valor.trim().replace(",", ".");
  if (!limpio) return undefined;
  const n = Number(limpio);
  return Number.isFinite(n) ? n : undefined;
}

/** Precio de venta vigente para mostrar y autocompletar. No descarta el 0. */
export function precioVentaVisible(articulo: Pick<ArticuloIngreso, "precio_venta">): string {
  const precio = Number(articulo.precio_venta);
  return Number.isFinite(precio) ? String(precio) : "";
}

/**
 * Solo envía precio si el usuario lo cambió respecto del vigente.
 * Vacío o igual al original es «sin cambios».
 */
export function precioVentaParaEnviar(
  precioOriginal: string | null,
  precioActual: string,
): number | undefined {
  const actual = numeroPrecio(precioActual);
  if (actual === undefined) return undefined;
  if (precioOriginal === null) return actual;
  const original = numeroPrecio(precioOriginal);
  if (original !== undefined && Math.abs(original - actual) < 0.001) return undefined;
  return actual;
}

export function barrasCambiaron(original: string, actual: string): boolean {
  return textoBarras(parseBarras(original)) !== textoBarras(parseBarras(actual));
}
