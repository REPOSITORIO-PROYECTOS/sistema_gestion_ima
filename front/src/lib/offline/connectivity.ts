import { API_CONFIG } from "@/lib/api-config";

export type OfflineConnectionStatus =
  | "online"
  | "browser_offline"
  | "server_unreachable";

export function isBrowserOnline(): boolean {
  if (typeof navigator === "undefined") return true;
  return navigator.onLine !== false;
}

export function getOfflineStatusLabel(status: OfflineConnectionStatus): string {
  if (status === "browser_offline") return "Sin conexión";
  if (status === "server_unreachable") return "Sin servidor";
  return "Conectado";
}

export async function pingServidor(
  token?: string | null,
  timeoutMs = 3000,
): Promise<boolean> {
  if (!isBrowserOnline()) return false;

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CAJA_ESTADO}`, {
      method: "GET",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      cache: "no-store",
      signal: controller.signal,
    });
    return true;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeout);
  }
}
