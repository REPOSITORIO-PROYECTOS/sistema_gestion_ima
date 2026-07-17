import { API_CONFIG } from "@/lib/api-config";
import { printPlainText } from "@/lib/printerService";
import {
  getOfflineMeta,
  offlineDb,
  upsertOfflineMeta,
  type CierrePendiente,
} from "@/lib/offline/db";
import { pingServidor } from "@/lib/offline/connectivity";

export type CierreCajaPayload = {
  id_sesion_caja: number;
  saldo_final_declarado: number;
  saldo_final_efectivo: number;
  saldo_final_transferencias: number;
  saldo_final_bancario: number;
  nombre_usuario?: string;
};

export type CerrarCajaSaldos = Omit<CierreCajaPayload, "id_sesion_caja" | "nombre_usuario">;

export type CerrarCajaResult =
  | { mode: "online"; id_sesion: number; message: string }
  | { mode: "offline"; id_local: string; message: string };

type CerrarCajaServidorResult =
  | { ok: true; id_sesion: number; message: string }
  | { ok: false; status: number; detail: string };

function newIdLocal(): string {
  return `cierre_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export function esErrorDeRed(error: unknown): boolean {
  if (error instanceof TypeError) return true;
  if (error instanceof DOMException && error.name === "AbortError") return true;
  if (error instanceof Error && /fetch|network|failed|abort/i.test(error.message)) {
    return true;
  }
  return false;
}

export function formatoMonedaAr(valor: number): string {
  return valor.toLocaleString("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function buildResumenCierreOfflineTexto(
  payload: CierreCajaPayload,
  empresaNombre?: string,
): string {
  const fecha = new Date().toLocaleString("es-AR", {
    timeZone: "America/Argentina/Buenos_Aires",
  });
  return [
    "=== CIERRE DE CAJA (OFFLINE) ===",
    empresaNombre ? `Negocio: ${empresaNombre}` : "",
    `Fecha: ${fecha}`,
    payload.nombre_usuario ? `Cajero: ${payload.nombre_usuario}` : "",
    `Sesión: ${payload.id_sesion_caja}`,
    "",
    `Efectivo:        $${formatoMonedaAr(payload.saldo_final_efectivo)}`,
    `Transferencias:  $${formatoMonedaAr(payload.saldo_final_transferencias)}`,
    `POS:             $${formatoMonedaAr(payload.saldo_final_bancario)}`,
    `TOTAL DECLARADO: $${formatoMonedaAr(payload.saldo_final_declarado)}`,
    "",
    "*** Pendiente de sincronizar con servidor ***",
  ]
    .filter(Boolean)
    .join("\n");
}

export async function guardarCierrePendiente(
  idEmpresa: number,
  payload: CierreCajaPayload,
): Promise<CierrePendiente> {
  const row: CierrePendiente = {
    id_local: newIdLocal(),
    id_empresa: idEmpresa,
    payload: JSON.stringify(payload),
    created_at: new Date().toISOString(),
    synced_at: null,
  };
  await offlineDb.cierres_pendientes.put(row);
  await upsertOfflineMeta(idEmpresa, { id_sesion_caja: null });
  return row;
}

export async function resolverIdSesionCajaLocal(
  idEmpresa: number,
  idSesionStore: number | null,
): Promise<number | null> {
  if (idSesionStore) return idSesionStore;
  const meta = await getOfflineMeta(idEmpresa);
  return meta?.id_sesion_caja ?? null;
}

export async function finalizarCierreOfflineLocal(params: {
  idEmpresa: number;
  idSesionCaja: number;
  saldos: CerrarCajaSaldos;
  nombreUsuario?: string;
  imprimir?: boolean;
  empresaNombre?: string;
}): Promise<CerrarCajaResult> {
  const payload: CierreCajaPayload = {
    id_sesion_caja: params.idSesionCaja,
    ...params.saldos,
    nombre_usuario: params.nombreUsuario,
  };
  const row = await guardarCierrePendiente(params.idEmpresa, payload);

  if (params.imprimir) {
    printPlainText(
      "Cierre de caja (offline)",
      buildResumenCierreOfflineTexto(payload, params.empresaNombre),
    );
  }

  return {
    mode: "offline",
    id_local: row.id_local,
    message: "Caja cerrada localmente. Se sincronizará al reconectar.",
  };
}

export async function cerrarCajaEnServidor(
  token: string,
  saldos: CerrarCajaSaldos,
): Promise<CerrarCajaServidorResult> {
  const res = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CAJA_CERRAR}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(saldos),
  });

  const data = (await res.json()) as {
    message?: string;
    detail?: string;
    data?: { id_sesion?: number };
  };

  if (!res.ok) {
    return {
      ok: false,
      status: res.status,
      detail: data.detail || data.message || res.statusText,
    };
  }

  return {
    ok: true,
    id_sesion: data.data?.id_sesion ?? 0,
    message: data.message || "Caja cerrada correctamente.",
  };
}

function esCierreYaProcesadoEnServidor(status: number, detail: string): boolean {
  if (status !== 404) return false;
  const normalizado = detail.toLowerCase();
  return (
    normalizado.includes("no tiene ninguna caja abierta") ||
    normalizado.includes("no está abierta")
  );
}

export async function sincronizarCierresPendientes(
  token: string,
  idEmpresa: number,
): Promise<{ sincronizados: number; errores: number }> {
  const tieneServidor = await pingServidor(token);
  if (!tieneServidor) {
    return { sincronizados: 0, errores: 0 };
  }

  const pendientes = await offlineDb.cierres_pendientes
    .where("id_empresa")
    .equals(idEmpresa)
    .filter((row) => !row.synced_at)
    .toArray();

  let sincronizados = 0;
  let errores = 0;

  for (const row of pendientes) {
    let payload: CierreCajaPayload;
    try {
      payload = JSON.parse(row.payload) as CierreCajaPayload;
    } catch {
      errores += 1;
      continue;
    }

    const saldos: CerrarCajaSaldos = {
      saldo_final_declarado: payload.saldo_final_declarado,
      saldo_final_efectivo: payload.saldo_final_efectivo,
      saldo_final_transferencias: payload.saldo_final_transferencias,
      saldo_final_bancario: payload.saldo_final_bancario,
    };

    try {
      const result = await cerrarCajaEnServidor(token, saldos);
      if (result.ok) {
        await offlineDb.cierres_pendientes.update(row.id_local, {
          synced_at: new Date().toISOString(),
        });
        sincronizados += 1;
        continue;
      }

      if (esCierreYaProcesadoEnServidor(result.status, result.detail)) {
        await offlineDb.cierres_pendientes.update(row.id_local, {
          synced_at: new Date().toISOString(),
        });
        sincronizados += 1;
        continue;
      }

      errores += 1;
    } catch (error) {
      if (esErrorDeRed(error)) break;
      errores += 1;
    }
  }

  return { sincronizados, errores };
}

export async function intentarCerrarCaja(params: {
  token: string;
  idEmpresa: number;
  offlineHabilitado: boolean;
  idSesionCaja: number | null;
  saldos: CerrarCajaSaldos;
  nombreUsuario?: string;
  imprimir?: boolean;
  empresaNombre?: string;
}): Promise<CerrarCajaResult> {
  try {
    const result = await cerrarCajaEnServidor(params.token, params.saldos);
    if (result.ok) {
      return {
        mode: "online",
        id_sesion: result.id_sesion,
        message: result.message,
      };
    }

    throw new Error(result.detail);
  } catch (error) {
    if (!params.offlineHabilitado || !esErrorDeRed(error)) {
      if (error instanceof Error) throw error;
      throw new Error("No se pudo cerrar la caja.");
    }

    const idSesion = await resolverIdSesionCajaLocal(
      params.idEmpresa,
      params.idSesionCaja,
    );
    if (!idSesion) {
      throw new Error(
        "Sin conexión y no hay sesión de caja local. Abrí la caja con internet antes de operar offline.",
      );
    }

    return finalizarCierreOfflineLocal({
      idEmpresa: params.idEmpresa,
      idSesionCaja: idSesion,
      saldos: params.saldos,
      nombreUsuario: params.nombreUsuario,
      imprimir: params.imprimir,
      empresaNombre: params.empresaNombre,
    });
  }
}
