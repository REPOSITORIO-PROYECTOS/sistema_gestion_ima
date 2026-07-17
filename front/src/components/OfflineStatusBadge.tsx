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

  const classByStatus =
    status.status === "online"
      ? "border-green-200 bg-green-50 text-green-800"
      : "border-amber-300 bg-amber-50 text-amber-900";

  const pendientes = status.pendingCount > 0 ? ` · ${status.pendingCount} pendientes` : "";

  return (
    <Badge variant="outline" className={`${classByStatus} ${className ?? ""}`}>
      {status.label}
      {pendientes}
    </Badge>
  );
}
