"use client";

import { useEffect, useState } from "react";
import { getOfflineMeta, type OfflineMeta } from "@/lib/offline/db";

export function useOfflineMeta(idEmpresa?: number, enabled = false) {
  const [meta, setMeta] = useState<OfflineMeta | undefined>();

  useEffect(() => {
    if (!enabled || !idEmpresa) {
      setMeta(undefined);
      return;
    }

    let cancelled = false;
    const load = async () => {
      const next = await getOfflineMeta(idEmpresa);
      if (!cancelled) setMeta(next);
    };

    void load();
    const interval = window.setInterval(load, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [enabled, idEmpresa]);

  return meta;
}
