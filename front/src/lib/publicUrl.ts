/**
 * Fuerza https en orígenes públicos para evitar bloqueos de contenido mixto en Chrome.
 * Conserva http en hosts locales usados en desarrollo.
 */
export function ensureHttpsPublicOrigin(url: string): string {
  const trimmed = url.trim();
  if (!trimmed) {
    return trimmed;
  }
  const lower = trimmed.toLowerCase();
  if (
    lower.startsWith("http://localhost") ||
    lower.startsWith("http://127.0.0.1") ||
    lower.startsWith("http://[::1]")
  ) {
    return trimmed;
  }
  if (trimmed.startsWith("http://")) {
    return `https://${trimmed.slice("http://".length)}`;
  }
  return trimmed;
}
