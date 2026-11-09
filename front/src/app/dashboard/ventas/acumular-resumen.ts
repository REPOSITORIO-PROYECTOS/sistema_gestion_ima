export type LineaResumen = {
  id?: string;
  tipo: string;
  cantidad: number;
  precioTotal: number;
  precioBase: number;
  descuentoAplicado: boolean;
  porcentajeDescuento: number;
  descuentoNominal: number;
};

const TOLERANCIA_PRECIO = 0.01;

function redondearCantidad(valor: number): number {
  return Math.round(valor * 1000) / 1000;
}

function redondearPlata(valor: number): number {
  return Math.round(valor * 100) / 100;
}

export function precioUnitarioLinea(linea: Pick<LineaResumen, "precioBase" | "cantidad">): number {
  if (!linea.cantidad) return linea.precioBase;
  return linea.precioBase / linea.cantidad;
}

function sinDescuentoDeLinea(linea: Pick<LineaResumen, "porcentajeDescuento" | "descuentoNominal">): boolean {
  return (linea.porcentajeDescuento || 0) === 0 && (linea.descuentoNominal || 0) === 0;
}

/**
 * Misma línea comercial: mismo artículo y mismo precio unitario, sin descuento
 * cargado en la línea. El código de barras (principal o alternativo) no entra:
 * el id ya es el del artículo. Un pesable se acumula igual, sumando el peso.
 * Si la línea ya tiene precio editado a otro valor, o un descuento, no se mezcla.
 */
export function puedeAcumular(existente: LineaResumen, nueva: LineaResumen): boolean {
  if (!existente.id || !nueva.id || existente.id !== nueva.id) return false;
  if (!sinDescuentoDeLinea(existente) || !sinDescuentoDeLinea(nueva)) return false;
  return Math.abs(precioUnitarioLinea(existente) - precioUnitarioLinea(nueva)) < TOLERANCIA_PRECIO;
}

export function acumularEnResumen(lineas: LineaResumen[], nueva: LineaResumen): LineaResumen[] {
  const indice = lineas.findIndex((linea) => puedeAcumular(linea, nueva));
  if (indice < 0) return [...lineas, nueva];

  const actual = lineas[indice];
  const cantidad = redondearCantidad(actual.cantidad + nueva.cantidad);
  const unitario = precioUnitarioLinea(actual);
  const precioBase = redondearPlata(unitario * cantidad);
  const copia = lineas.slice();
  copia[indice] = {
    ...actual,
    cantidad,
    precioBase,
    precioTotal: precioBase,
    descuentoAplicado: false,
    porcentajeDescuento: 0,
    descuentoNominal: 0,
  };
  return copia;
}
