import { offlineDb, type OfflineArticulo } from "@/lib/offline/db";
import { obtenerCantidadesPendientesPorArticulo } from "@/lib/offline/venta-offline";
import { calcularStockVisible } from "@/lib/offline/stock-visible";

export type ProductoOffline = {
  id: string;
  nombre: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
  unidad_venta: string;
  precio_manual?: boolean;
};

export function mapOfflineArticuloToProducto(
  articulo: OfflineArticulo,
  pendientesPorArticulo?: Record<string, number>,
): ProductoOffline {
  const pendiente = pendientesPorArticulo?.[articulo.id] ?? 0;
  return {
    id: articulo.id,
    nombre: articulo.descripcion,
    precio_venta: articulo.precio_venta,
    venta_negocio: articulo.venta_negocio,
    stock_actual: calcularStockVisible(articulo.stock_snapshot, pendiente),
    unidad_venta: articulo.unidad_venta,
    precio_manual: articulo.precio_manual,
  };
}

export async function buscarArticulosLocal(
  idEmpresa: number,
  termino: string,
  limit = 40,
): Promise<ProductoOffline[]> {
  const q = termino.trim().toLocaleLowerCase("es-AR");
  const [articulos, pendientesPorArticulo] = await Promise.all([
    offlineDb.articulos.where("id_empresa").equals(idEmpresa).toArray(),
    obtenerCantidadesPendientesPorArticulo(idEmpresa),
  ]);

  return articulos
    .filter((articulo) => {
      if (!articulo.activo) return false;
      if (!q) return true;
      const descripcion = articulo.descripcion.toLocaleLowerCase("es-AR");
      const codigoInterno = articulo.codigo_interno?.toLocaleLowerCase("es-AR") ?? "";
      return descripcion.includes(q) || codigoInterno.includes(q);
    })
    .slice(0, limit)
    .map((articulo) => mapOfflineArticuloToProducto(articulo, pendientesPorArticulo));
}

export async function buscarPorCodigoLocal(
  idEmpresa: number,
  codigo: string,
): Promise<ProductoOffline | null> {
  const codigoNormalizado = codigo.trim();
  if (!codigoNormalizado) return null;

  const row = await offlineDb.codigos_barras.get(codigoNormalizado);
  if (!row || row.id_empresa !== idEmpresa) return null;

  const [articulo, pendientesPorArticulo] = await Promise.all([
    offlineDb.articulos.get(row.id_articulo),
    obtenerCantidadesPendientesPorArticulo(idEmpresa),
  ]);
  if (!articulo || articulo.id_empresa !== idEmpresa || !articulo.activo) return null;

  return mapOfflineArticuloToProducto(articulo, pendientesPorArticulo);
}
