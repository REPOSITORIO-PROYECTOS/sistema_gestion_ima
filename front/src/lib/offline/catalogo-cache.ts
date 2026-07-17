import {
  fetchAllArticulos,
  fetchCatalogoVersion,
  type ArticuloCatalogoAPI,
} from "@/lib/articulos-api";
import {
  clearOfflineEmpresa,
  getOfflineMeta,
  offlineDb,
  upsertOfflineMeta,
  type OfflineArticulo,
  type OfflineCodigoBarras,
} from "@/lib/offline/db";

export type RefreshCatalogoResult = {
  refreshed: boolean;
  catalogo_version: number;
  articulos_count: number;
  codigos_count: number;
};

function mapArticuloOffline(
  item: ArticuloCatalogoAPI,
  idEmpresa: number,
): OfflineArticulo {
  const stock = item.stock_actual ?? 0;
  return {
    id: String(item.id),
    id_empresa: idEmpresa,
    descripcion: item.descripcion ?? item.nombre ?? "",
    precio_venta: item.precio_venta,
    venta_negocio: item.venta_negocio,
    stock_actual: stock,
    stock_snapshot: stock,
    unidad_venta: item.unidad_venta || "unidad",
    precio_manual: item.precio_manual ?? false,
    activo: item.activo ?? true,
    codigo_interno: item.codigo_interno ?? null,
  };
}

function mapCodigosBarras(
  items: ArticuloCatalogoAPI[],
  idEmpresa: number,
): OfflineCodigoBarras[] {
  const rows: OfflineCodigoBarras[] = [];
  for (const item of items) {
    const idArticulo = String(item.id);
    for (const entry of item.codigos ?? []) {
      const codigo = entry.codigo?.trim();
      if (!codigo) continue;
      rows.push({
        codigo,
        id_articulo: idArticulo,
        id_empresa: idEmpresa,
      });
    }
    const interno = item.codigo_interno?.trim();
    if (interno) {
      rows.push({
        codigo: interno,
        id_articulo: idArticulo,
        id_empresa: idEmpresa,
      });
    }
  }
  return rows;
}

/** Full refresh de catálogo + stock snapshot en IndexedDB (abrir/cerrar caja). */
export async function refreshCatalogoCache(
  token: string,
  idEmpresa: number,
  options?: { force?: boolean },
): Promise<RefreshCatalogoResult> {
  if (!token || !idEmpresa) {
    throw new Error("Token e id_empresa son requeridos para refrescar caché.");
  }

  const remoteVersion = await fetchCatalogoVersion(token);
  const meta = await getOfflineMeta(idEmpresa);

  if (
    !options?.force &&
    meta &&
    meta.catalogo_version === remoteVersion &&
    meta.catalogo_synced_at
  ) {
    const count = await offlineDb.articulos.where("id_empresa").equals(idEmpresa).count();
    return {
      refreshed: false,
      catalogo_version: remoteVersion,
      articulos_count: count,
      codigos_count: await offlineDb.codigos_barras.where("id_empresa").equals(idEmpresa).count(),
    };
  }

  const articulos = await fetchAllArticulos(token);
  const offlineArticulos = articulos.map((item) => mapArticuloOffline(item, idEmpresa));
  const codigos = mapCodigosBarras(articulos, idEmpresa);
  const syncedAt = new Date().toISOString();

  await offlineDb.transaction(
    "rw",
    offlineDb.articulos,
    offlineDb.codigos_barras,
    offlineDb.meta,
    async () => {
      await offlineDb.articulos.where("id_empresa").equals(idEmpresa).delete();
      await offlineDb.codigos_barras.where("id_empresa").equals(idEmpresa).delete();
      if (offlineArticulos.length > 0) {
        await offlineDb.articulos.bulkPut(offlineArticulos);
      }
      if (codigos.length > 0) {
        await offlineDb.codigos_barras.bulkPut(codigos);
      }
      await upsertOfflineMeta(idEmpresa, {
        catalogo_version: remoteVersion,
        catalogo_synced_at: syncedAt,
        stock_snapshot_at: syncedAt,
      });
    },
  );

  return {
    refreshed: true,
    catalogo_version: remoteVersion,
    articulos_count: offlineArticulos.length,
    codigos_count: codigos.length,
  };
}

export async function ensureOfflineEmpresa(
  token: string,
  idEmpresa: number,
): Promise<void> {
  const meta = await getOfflineMeta(idEmpresa);
  if (meta && meta.id_empresa === idEmpresa) return;
  await clearOfflineEmpresa(idEmpresa);
  await upsertOfflineMeta(idEmpresa, {
    catalogo_version: 0,
    catalogo_synced_at: null,
    stock_snapshot_at: null,
    id_sesion_caja: null,
  });
  if (token) {
    await refreshCatalogoCache(token, idEmpresa, { force: true });
  }
}
