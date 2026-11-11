"use client";

import { useEffect, useRef } from "react";
import { isBrowserOnline, pingServidor } from "@/lib/offline/connectivity";
import type { ArticuloCatalogoAPI } from "@/lib/articulos-api";
import { refreshCatalogoCache } from "@/lib/offline/catalogo-cache";
import {
  crearRefrescoPeriodico,
  intervaloRefrescoCatalogoMs,
} from "@/lib/offline/catalogo-refresh-scheduler";

type CatalogoAutoRefreshParams = {
  enabled: boolean;
  token?: string | null;
  idEmpresa?: number;
  intervalMs?: number;
  onCatalogo?: (articulos: ArticuloCatalogoAPI[]) => void;
};

/**
 * Mientras la caja está abierta y hay servidor, renueva el catálogo local.
 * Sin red no pide nada. Al volver `online` o al mostrar la pestaña, reintenta.
 */
export function useCatalogoAutoRefresh({
  enabled,
  token,
  idEmpresa,
  intervalMs,
  onCatalogo,
}: CatalogoAutoRefreshParams): void {
  const onCatalogoRef = useRef(onCatalogo);
  onCatalogoRef.current = onCatalogo;

  useEffect(() => {
    if (!enabled || !token || !idEmpresa) return;

    const scheduler = crearRefrescoPeriodico({
      intervalMs: intervalMs ?? intervaloRefrescoCatalogoMs(),
      hayConexion: async () => {
        if (!isBrowserOnline()) return false;
        return pingServidor(token);
      },
      refrescar: async () => {
        const resultado = await refreshCatalogoCache(token, idEmpresa, { force: true });
        if (resultado.articulos) onCatalogoRef.current?.(resultado.articulos);
      },
    });

    const alVolverLaRed = () => {
      void scheduler.tick();
    };
    const alMostrarPestaña = () => {
      if (document.visibilityState === "visible") alVolverLaRed();
    };

    window.addEventListener("online", alVolverLaRed);
    document.addEventListener("visibilitychange", alMostrarPestaña);
    scheduler.start();
    void scheduler.tick();

    return () => {
      scheduler.stop();
      window.removeEventListener("online", alVolverLaRed);
      document.removeEventListener("visibilitychange", alMostrarPestaña);
    };
  }, [enabled, token, idEmpresa, intervalMs]);
}
