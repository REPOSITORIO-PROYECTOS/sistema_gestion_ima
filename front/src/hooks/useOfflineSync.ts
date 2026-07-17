"use client";

import { useEffect, useRef } from "react";
import { toast } from "sonner";
import { sincronizarCierresPendientes } from "@/lib/offline/cierre-caja";
import { sincronizarVentasPendientes } from "@/lib/offline/venta-offline";
import { isBrowserOnline, pingServidor } from "@/lib/offline/connectivity";

type OfflineSyncParams = {
  enabled: boolean;
  token?: string | null;
  idEmpresa?: number;
};

export function useOfflineSync({ enabled, token, idEmpresa }: OfflineSyncParams): void {
  const syncingRef = useRef(false);

  useEffect(() => {
    if (!enabled || !token || !idEmpresa) return;

    let cancelled = false;

    const syncPendientes = async () => {
      if (syncingRef.current || cancelled) return;
      if (!isBrowserOnline()) return;

      const tieneServidor = await pingServidor(token);
      if (!tieneServidor || cancelled) return;

      syncingRef.current = true;
      try {
        const ventas = await sincronizarVentasPendientes(token, idEmpresa);
        const cierres = await sincronizarCierresPendientes(token, idEmpresa);
        if (cancelled) return;

        if (ventas.sincronizados > 0) {
          toast.success(
            ventas.sincronizados === 1
              ? "Venta offline sincronizada con el servidor."
              : `${ventas.sincronizados} ventas offline sincronizadas.`,
          );
        }
        if (ventas.errores > 0) {
          toast.warning(
            ventas.errores === 1
              ? "Quedó 1 venta pendiente de sincronizar."
              : `Quedaron ${ventas.errores} ventas pendientes de sincronizar.`,
          );
        }

        if (cierres.sincronizados > 0) {
          toast.success(
            cierres.sincronizados === 1
              ? "Cierre de caja sincronizado con el servidor."
              : `${cierres.sincronizados} cierres de caja sincronizados.`,
          );
        }
        if (cierres.errores > 0) {
          toast.warning(
            cierres.errores === 1
              ? "Quedó 1 cierre de caja pendiente de sincronizar."
              : `Quedaron ${cierres.errores} cierres de caja pendientes de sincronizar.`,
          );
        }
      } finally {
        syncingRef.current = false;
      }
    };

    const onOnline = () => {
      void syncPendientes();
    };

    void syncPendientes();
    window.addEventListener("online", onOnline);
    const interval = window.setInterval(syncPendientes, 60_000);

    return () => {
      cancelled = true;
      window.removeEventListener("online", onOnline);
      window.clearInterval(interval);
    };
  }, [enabled, idEmpresa, token]);
}
