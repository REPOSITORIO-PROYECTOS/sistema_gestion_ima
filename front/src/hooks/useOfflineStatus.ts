"use client";

import { useEffect, useState } from "react";
import {
  getOfflineStatusLabel,
  isBrowserOnline,
  pingServidor,
  type OfflineConnectionStatus,
} from "@/lib/offline/connectivity";
import { offlineDb } from "@/lib/offline/db";

type OfflineStatusState = {
  status: OfflineConnectionStatus;
  label: string;
  pendingCount: number;
};

const ONLINE_STATE: OfflineStatusState = {
  status: "online",
  label: getOfflineStatusLabel("online"),
  pendingCount: 0,
};

async function contarPendientes(idEmpresa?: number): Promise<number> {
  if (!idEmpresa) return 0;
  const [ventas, cierres] = await Promise.all([
    offlineDb.ventas_pendientes.where("id_empresa").equals(idEmpresa).count(),
    offlineDb.cierres_pendientes.where("id_empresa").equals(idEmpresa).count(),
  ]);
  return ventas + cierres;
}

export function useOfflineStatus(params: {
  enabled: boolean;
  token?: string | null;
  idEmpresa?: number;
}): OfflineStatusState {
  const { enabled, token, idEmpresa } = params;
  const [state, setState] = useState<OfflineStatusState>(ONLINE_STATE);

  useEffect(() => {
    if (!enabled) {
      setState(ONLINE_STATE);
      return;
    }

    let cancelled = false;

    const refresh = async () => {
      const pendingCount = await contarPendientes(idEmpresa);
      if (!isBrowserOnline()) {
        if (!cancelled) {
          setState({
            status: "browser_offline",
            label: getOfflineStatusLabel("browser_offline"),
            pendingCount,
          });
        }
        return;
      }

      const hasServer = await pingServidor(token);
      if (!cancelled) {
        const status: OfflineConnectionStatus = hasServer ? "online" : "server_unreachable";
        setState({
          status,
          label: getOfflineStatusLabel(status),
          pendingCount,
        });
      }
    };

    const onConnectivityChange = () => {
      void refresh();
    };

    void refresh();
    window.addEventListener("online", onConnectivityChange);
    window.addEventListener("offline", onConnectivityChange);
    const interval = window.setInterval(refresh, 30_000);

    return () => {
      cancelled = true;
      window.removeEventListener("online", onConnectivityChange);
      window.removeEventListener("offline", onConnectivityChange);
      window.clearInterval(interval);
    };
  }, [enabled, idEmpresa, token]);

  return state;
}
