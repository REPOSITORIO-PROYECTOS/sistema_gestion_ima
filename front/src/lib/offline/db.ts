import Dexie, { type Table } from "dexie";

export type OfflineMeta = {
  key: string;
  id_empresa: number;
  catalogo_version: number;
  catalogo_synced_at: string | null;
  stock_snapshot_at: string | null;
  id_sesion_caja: number | null;
};

export type OfflineArticulo = {
  id: string;
  id_empresa: number;
  descripcion: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
  stock_snapshot: number;
  unidad_venta: string;
  precio_manual: boolean;
  activo: boolean;
  codigo_interno?: string | null;
};

export type OfflineCodigoBarras = {
  codigo: string;
  id_articulo: string;
  id_empresa: number;
};

export type VentaPendienteEstado =
  | "pendiente"
  | "sincronizando"
  | "sincronizado"
  | "conflicto"
  | "error";

export type VentaPendiente = {
  id_local: string;
  id_empresa: number;
  estado: VentaPendienteEstado;
  payload: string;
  snapshot_version: number;
  id_sesion_caja_cache: number;
  created_at: string;
  synced_at: string | null;
  conflicto_motivo?: string | null;
  conflicto_unidades?: number | null;
};

export type CierrePendiente = {
  id_local: string;
  id_empresa: number;
  payload: string;
  created_at: string;
  synced_at: string | null;
};

const META_KEYS = {
  empresa: "empresa",
} as const;

class OfflineDatabase extends Dexie {
  meta!: Table<OfflineMeta, string>;
  articulos!: Table<OfflineArticulo, string>;
  codigos_barras!: Table<OfflineCodigoBarras, string>;
  ventas_pendientes!: Table<VentaPendiente, string>;
  cierres_pendientes!: Table<CierrePendiente, string>;

  constructor() {
    super("ima_offline_v1");
    this.version(1).stores({
      meta: "key",
      articulos: "id, id_empresa, descripcion",
      codigos_barras: "codigo, id_articulo, id_empresa",
      ventas_pendientes: "id_local, id_empresa, estado, created_at",
      cierres_pendientes: "id_local, id_empresa, created_at",
    });
  }
}

export const offlineDb = new OfflineDatabase();

export async function getOfflineMeta(idEmpresa: number): Promise<OfflineMeta | undefined> {
  return offlineDb.meta.get(`${META_KEYS.empresa}:${idEmpresa}`);
}

export async function upsertOfflineMeta(
  idEmpresa: number,
  patch: Partial<Omit<OfflineMeta, "key" | "id_empresa">>,
): Promise<OfflineMeta> {
  const key = `${META_KEYS.empresa}:${idEmpresa}`;
  const existing = await offlineDb.meta.get(key);
  const hasPatchValue = <K extends keyof typeof patch>(field: K): boolean =>
    Object.prototype.hasOwnProperty.call(patch, field);
  const next: OfflineMeta = {
    key,
    id_empresa: idEmpresa,
    catalogo_version: hasPatchValue("catalogo_version")
      ? patch.catalogo_version ?? 0
      : existing?.catalogo_version ?? 0,
    catalogo_synced_at: hasPatchValue("catalogo_synced_at")
      ? patch.catalogo_synced_at ?? null
      : existing?.catalogo_synced_at ?? null,
    stock_snapshot_at: hasPatchValue("stock_snapshot_at")
      ? patch.stock_snapshot_at ?? null
      : existing?.stock_snapshot_at ?? null,
    id_sesion_caja: hasPatchValue("id_sesion_caja")
      ? patch.id_sesion_caja ?? null
      : existing?.id_sesion_caja ?? null,
  };
  await offlineDb.meta.put(next);
  return next;
}

export async function clearOfflineEmpresa(idEmpresa: number): Promise<void> {
  await offlineDb.meta.delete(`${META_KEYS.empresa}:${idEmpresa}`);
  await offlineDb.articulos.where("id_empresa").equals(idEmpresa).delete();
  await offlineDb.codigos_barras.where("id_empresa").equals(idEmpresa).delete();
  await offlineDb.ventas_pendientes.where("id_empresa").equals(idEmpresa).delete();
  await offlineDb.cierres_pendientes.where("id_empresa").equals(idEmpresa).delete();
}
