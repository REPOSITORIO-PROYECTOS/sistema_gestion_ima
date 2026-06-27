import {
  fetchArticuloPorId,
  mapArticulosToStore,
} from "./articulos-api";
import type { Producto } from "./productoStore";

/** Actualiza en cache solo los productos indicados (p. ej. tras una venta). */
export async function actualizarProductosEnCache(
  token: string,
  ids: string[],
  upsertProductos: (productos: Producto[]) => void,
): Promise<void> {
  const idsUnicos = [...new Set(ids.filter(Boolean))];
  if (idsUnicos.length === 0) return;

  const resultados = await Promise.all(
    idsUnicos.map((id) => fetchArticuloPorId(token, id)),
  );

  const adaptados = mapArticulosToStore(
    resultados.filter((a): a is NonNullable<typeof a> => a !== null),
  );

  if (adaptados.length > 0) {
    upsertProductos(adaptados);
  }
}
