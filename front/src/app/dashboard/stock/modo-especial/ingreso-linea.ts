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

export function codigosCambiaron(original: string[], actual: string[]): boolean {
  return textoBarras(original) !== textoBarras(actual);
}

export type AgregarAlternativo =
  | { ok: true; alternativos: string[] }
  | { ok: false; motivo: "vacio" | "duplicado" };

/** Enter agrega un alternativo. No repite el principal ni otro alternativo. */
export function agregarAlternativo(
  principal: string,
  alternativos: string[],
  nuevo: string,
): AgregarAlternativo {
  const codigo = nuevo.trim();
  if (!codigo) return { ok: false, motivo: "vacio" };
  const yaEsta = codigo === principal.trim() || alternativos.some((item) => item.trim() === codigo);
  if (yaEsta) return { ok: false, motivo: "duplicado" };
  return { ok: true, alternativos: [...alternativos, codigo] };
}

/** El primero es el principal. El resto son alternativos, sin repetir. */
export function unirCodigos(principal: string, alternativos: string[]): string[] {
  const cabeza = principal.trim();
  const cola = alternativos.map((item) => item.trim()).filter((item) => item && item !== cabeza);
  return parseBarras([cabeza, ...cola].filter(Boolean).join(", "));
}

export const DESTINO_ESTA_SUCURSAL = "local";

export function esDestinoLocal(destinoId: string): boolean {
  return !destinoId || destinoId === DESTINO_ESTA_SUCURSAL;
}

export function textoDestinoIngreso(destinoNombre: string | null): string {
  if (!destinoNombre) {
    return "Esta sucursal: el stock se suma acá, igual que un ingreso común.";
  }
  return `Envío a ${destinoNombre}: la mercadería entra y sale de esta sucursal. Queda pendiente de recepción allá; el stock de destino suma recién cuando la reciben.`;
}
