"use client";

import { Badge } from "@/components/ui/badge";
import { useOfflineStatus } from "@/hooks/useOfflineStatus";

type OfflineStatusBadgeProps = {
  enabled: boolean;
  token?: string | null;
  idEmpresa?: number;
  className?: string;
};

export function OfflineStatusBadge({
  enabled,
  token,
  idEmpresa,
  className,
}: OfflineStatusBadgeProps) {
  const status = useOfflineStatus({ enabled, token, idEmpresa });

  if (!enabled) return null;
  // Solo mostrar cuando hay problema de conexión (no el membrete "Conectado").
  if (status.status === "online") return null;

  const pendientes = status.pendingCount > 0 ? ` · ${status.pendingCount} pendientes` : "";

  return (
    <Badge
      variant="outline"
      className={`border-amber-300 bg-amber-50 text-amber-900 ${className ?? ""}`}
    >
      {status.label}
      {pendientes}
    </Badge>
  );
}
