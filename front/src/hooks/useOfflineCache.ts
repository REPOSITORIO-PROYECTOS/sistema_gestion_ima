"use client";

import { useCallback } from "react";
import {
  refreshCatalogoCache,
  type RefreshCatalogoResult,
} from "@/lib/offline/catalogo-cache";
import { getOfflineMeta, upsertOfflineMeta } from "@/lib/offline/db";

type OfflineCacheParams = {
  token?: string | null;
  idEmpresa?: number;
  enabled: boolean;
};

export function useOfflineCache({ token, idEmpresa, enabled }: OfflineCacheParams) {
  const refrescar = useCallback(
    async (idSesionCaja?: number | null): Promise<RefreshCatalogoResult | null> => {
      if (!enabled || !token || !idEmpresa) return null;
      const result = await refreshCatalogoCache(token, idEmpresa, { force: true });
      if (typeof idSesionCaja !== "undefined") {
        await upsertOfflineMeta(idEmpresa, { id_sesion_caja: idSesionCaja });
      }
      return result;
    },
    [enabled, idEmpresa, token],
  );

  const refrescarTrasAperturaCaja = useCallback(
    (idSesionCaja: number) => refrescar(idSesionCaja),
    [refrescar],
  );

  const refrescarTrasCierreCaja = useCallback(
    async () => {
      const result = await refrescar(null);
      if (enabled && idEmpresa) {
        await upsertOfflineMeta(idEmpresa, { id_sesion_caja: null });
      }
      return result;
    },
    [enabled, idEmpresa, refrescar],
  );

  const tieneCache = useCallback(async () => {
    if (!idEmpresa) return false;
    const meta = await getOfflineMeta(idEmpresa);
    return Boolean(meta?.catalogo_synced_at);
  }, [idEmpresa]);

  return {
    refrescarTrasAperturaCaja,
    refrescarTrasCierreCaja,
    tieneCache,
  };
}
