/** Stock visible en pantalla = snapshot al abrir/cerrar caja − ventas pendientes locales. */
export function calcularStockVisible(
  stockSnapshot: number,
  cantidadPendienteLocal = 0,
): number {
  return Math.max(0, stockSnapshot - cantidadPendienteLocal);
}

export function agruparPendientesPorArticulo(
  pendientes: Array<{ id_articulo: string; cantidad: number }>,
): Record<string, number> {
  return pendientes.reduce<Record<string, number>>((acc, item) => {
    const key = String(item.id_articulo);
    acc[key] = (acc[key] ?? 0) + item.cantidad;
    return acc;
  }, {});
}
