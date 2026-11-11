import {
  fetchCatalogoCompleto,
  fetchCatalogoVersion,
  type ArticuloCatalogoAPI,
  type CatalogoDescarga,
  type FetchCatalogoOptions,
} from "@/lib/articulos-api";
import { publicarCatalogoVigente } from "@/lib/offline/catalogo-vigente";
import {
  ESQUEMA_CODIGOS_BARRAS,
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
  articulos?: ArticuloCatalogoAPI[];
};

export type RefreshCatalogoOptions = FetchCatalogoOptions & {
  force?: boolean;
};

let descargaEnCurso: Promise<RefreshCatalogoResult> | null = null;

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
  const vistos = new Set<string>();
  const agregar = (idArticulo: string, codigo: string) => {
    const limpio = codigo.trim();
    if (!limpio) return;
    const clave = `${idEmpresa}:${limpio}`;
    if (vistos.has(clave)) return;
    vistos.add(clave);
    rows.push({
      codigo: limpio,
      id_articulo: idArticulo,
      id_empresa: idEmpresa,
    });
  };
  for (const item of items) {
    const idArticulo = String(item.id);
    for (const entry of item.codigos ?? []) {
      agregar(idArticulo, entry.codigo ?? "");
    }
    agregar(idArticulo, item.codigo_interno ?? "");
  }
  return rows;
}

async function persistirCatalogoCompleto(
  idEmpresa: number,
  descarga: CatalogoDescarga,
): Promise<void> {
  if (descarga.articulos.length !== descarga.total) {
    throw new Error("Catálogo incompleto: no se reemplaza la caché.");
  }

  const offlineArticulos = descarga.articulos.map((item) => mapArticuloOffline(item, idEmpresa));
  const codigos = mapCodigosBarras(descarga.articulos, idEmpresa);
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
        catalogo_version: descarga.version,
        catalogo_synced_at: syncedAt,
        stock_snapshot_at: syncedAt,
        codigos_schema: ESQUEMA_CODIGOS_BARRAS,
      });
    },
  );
}

async function descargarYPersistir(
  token: string,
  idEmpresa: number,
  options?: FetchCatalogoOptions,
): Promise<RefreshCatalogoResult> {
  const descarga = await fetchCatalogoCompleto(token, options);
  await persistirCatalogoCompleto(idEmpresa, descarga);
  publicarCatalogoVigente(idEmpresa, descarga.articulos);
  return {
    refreshed: true,
    catalogo_version: descarga.version,
    articulos_count: descarga.articulos.length,
    codigos_count: mapCodigosBarras(descarga.articulos, idEmpresa).length,
    articulos: descarga.articulos,
  };
}

/** Full refresh de catálogo + stock snapshot en IndexedDB (abrir/cerrar caja y refresco periódico). */
export async function refreshCatalogoCache(
  token: string,
  idEmpresa: number,
  options?: RefreshCatalogoOptions,
): Promise<RefreshCatalogoResult> {
  if (!token || !idEmpresa) {
    throw new Error("Token e id_empresa son requeridos para refrescar caché.");
  }

  if (!options?.force) {
    const remoteVersion = await fetchCatalogoVersion(token);
    const meta = await getOfflineMeta(idEmpresa);
    if (
      meta &&
      meta.catalogo_version === remoteVersion &&
      meta.catalogo_synced_at &&
      (meta.codigos_schema ?? 1) === ESQUEMA_CODIGOS_BARRAS
    ) {
      const count = await offlineDb.articulos.where("id_empresa").equals(idEmpresa).count();
      return {
        refreshed: false,
        catalogo_version: remoteVersion,
        articulos_count: count,
        codigos_count: await offlineDb.codigos_barras.where("id_empresa").equals(idEmpresa).count(),
      };
    }
  }

  if (descargaEnCurso) return descargaEnCurso;

  let resolveTrabajo: (resultado: RefreshCatalogoResult) => void = () => undefined;
  let rejectTrabajo: (error: unknown) => void = () => undefined;
  const trabajo = new Promise<RefreshCatalogoResult>((resolve, reject) => {
    resolveTrabajo = resolve;
    rejectTrabajo = reject;
  });
  descargaEnCurso = trabajo;

  void descargarYPersistir(token, idEmpresa, options).then(
    (resultado) => resolveTrabajo(resultado),
    (error: unknown) => rejectTrabajo(error),
  ).finally(() => {
    if (descargaEnCurso === trabajo) descargaEnCurso = null;
  });

  return trabajo;
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
