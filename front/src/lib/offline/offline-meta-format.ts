export function formatSnapshotAge(isoDate: string | null | undefined): string | null {
  if (!isoDate) return null;

  const parsed = new Date(isoDate);
  if (Number.isNaN(parsed.getTime())) return null;

  const diffMs = Date.now() - parsed.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays >= 1) {
    return `hace ${diffDays} día${diffDays === 1 ? "" : "s"}`;
  }
  if (diffHours >= 1) {
    return `hace ${diffHours} hora${diffHours === 1 ? "" : "s"}`;
  }
  return "hace menos de 1 hora";
}

export function mensajeSnapshotDesactualizado(
  stockSnapshotAt: string | null | undefined,
): string | null {
  const age = formatSnapshotAge(stockSnapshotAt);
  if (!age) return "Precios y stock pueden no estar actualizados.";
  return `Precios y stock pueden no estar actualizados (snapshot ${age}).`;
}
