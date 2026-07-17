import { API_CONFIG } from "@/lib/api-config";
import { printPlainText, downloadPlainText } from "@/lib/printerService";
import {
  getOfflineMeta,
  offlineDb,
  type VentaPendiente,
  type VentaPendienteEstado,
} from "@/lib/offline/db";
import { pingServidor } from "@/lib/offline/connectivity";
import { esErrorDeRed, formatoMonedaAr, resolverIdSesionCajaLocal } from "@/lib/offline/cierre-caja";
import { agruparPendientesPorArticulo } from "@/lib/offline/stock-visible";

export type ArticuloVendidoPayload = {
  id_articulo: number;
  nombre?: string;
  cantidad: number;
  precio_unitario: number;
  subtotal?: number;
  tasa_iva?: number;
};

export type RegistrarVentaBody = {
  id_cliente: number;
  total_venta: number;
  descuento_total: number;
  paga_con: number;
  pago_separado: boolean;
  detalles_pago_separado: string;
  tipo_comprobante_solicitado: string;
  quiere_factura: boolean;
  articulos_vendidos: ArticuloVendidoPayload[];
  metodo_pago?: string;
  pagos_multiples?: Array<{ metodo_pago: string; monto: number }>;
};

export type VentaPendienteMeta = {
  tipo_comprobante: string;
  observaciones: string;
  total_final: number;
  descuento_nominal_total: number;
  descuento_sobre_total: number;
  cliente_nombre: string;
  cuit_receptor: string;
  empresa_nombre?: string;
};

export type VentaPendientePayload = {
  venta: RegistrarVentaBody;
  meta: VentaPendienteMeta;
};

export type RegistrarVentaResult =
  | { mode: "online"; message: string }
  | { mode: "offline"; id_local: string; message: string };

type RegistrarVentaServidorResult =
  | { ok: true; message: string }
  | { ok: false; status: number; detail: string };

const ESTADOS_REINTENTABLES: VentaPendienteEstado[] = ["pendiente", "error"];

function newIdLocal(): string {
  return `venta_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export function esFacturaOfflineNoPermitida(
  tipoComprobante: string,
  quiereFactura: boolean,
): boolean {
  const tipo = tipoComprobante.toLowerCase();
  return quiereFactura || tipo === "factura" || tipo.startsWith("factura_");
}

export function buildComprobanteOfflineTexto(
  payload: VentaPendientePayload,
  idLocal: string,
): string {
  const fecha = new Date().toLocaleString("es-AR", {
    timeZone: "America/Argentina/Buenos_Aires",
  });
  const lineas = payload.venta.articulos_vendidos.map((item) => {
    const subtotal = item.subtotal ?? item.precio_unitario * item.cantidad;
    const nombre = item.nombre ?? `Artículo ${item.id_articulo}`;
    return `${nombre.padEnd(22).slice(0, 22)} x${String(item.cantidad).padStart(4)}  $${formatoMonedaAr(subtotal)}`;
  });

  return [
    `=== COMPROBANTE ${payload.meta.tipo_comprobante.toUpperCase()} (OFFLINE) ===`,
    payload.meta.empresa_nombre ? `Negocio: ${payload.meta.empresa_nombre}` : "",
    `Fecha: ${fecha}`,
    `Cliente: ${payload.meta.cliente_nombre}`,
    payload.meta.cuit_receptor && payload.meta.cuit_receptor !== "0"
      ? `CUIT/DNI: ${payload.meta.cuit_receptor}`
      : "",
    "",
    ...lineas,
    "",
    `TOTAL: $${formatoMonedaAr(payload.meta.total_final)}`,
    payload.meta.descuento_nominal_total > 0
      ? `Desc. $: $${formatoMonedaAr(payload.meta.descuento_nominal_total)}`
      : "",
    payload.meta.descuento_sobre_total > 0
      ? `Desc. %: ${payload.meta.descuento_sobre_total}%`
      : "",
    payload.meta.observaciones ? `Obs: ${payload.meta.observaciones}` : "",
    "",
    `Ref. local: ${idLocal}`,
    "*** Pendiente de sincronizar con servidor ***",
  ]
    .filter(Boolean)
    .join("\n");
}

export function imprimirComprobanteOffline(
  payload: VentaPendientePayload,
  idLocal: string,
): void {
  const texto = buildComprobanteOfflineTexto(payload, idLocal);
  const nombreArchivo = `Comprobante_offline_${idLocal}.txt`;
  downloadPlainText(nombreArchivo, texto);
  printPlainText(`Comprobante ${payload.meta.tipo_comprobante}`, texto);
}

export async function obtenerCantidadesPendientesPorArticulo(
  idEmpresa: number,
): Promise<Record<string, number>> {
  const rows = await offlineDb.ventas_pendientes
    .where("id_empresa")
    .equals(idEmpresa)
    .filter((row) => ESTADOS_REINTENTABLES.includes(row.estado))
    .toArray();

  const items: Array<{ id_articulo: string; cantidad: number }> = [];
  for (const row of rows) {
    try {
      const payload = JSON.parse(row.payload) as VentaPendientePayload;
      for (const articulo of payload.venta.articulos_vendidos) {
        items.push({
          id_articulo: String(articulo.id_articulo),
          cantidad: articulo.cantidad,
        });
      }
    } catch {
      continue;
    }
  }

  return agruparPendientesPorArticulo(items);
}

export async function guardarVentaPendiente(params: {
  idEmpresa: number;
  idSesionCaja: number;
  snapshotVersion: number;
  payload: VentaPendientePayload;
}): Promise<VentaPendiente> {
  const row: VentaPendiente = {
    id_local: newIdLocal(),
    id_empresa: params.idEmpresa,
    estado: "pendiente",
    payload: JSON.stringify(params.payload),
    snapshot_version: params.snapshotVersion,
    id_sesion_caja_cache: params.idSesionCaja,
    created_at: new Date().toISOString(),
    synced_at: null,
    conflicto_motivo: null,
    conflicto_unidades: null,
  };
  await offlineDb.ventas_pendientes.put(row);
  return row;
}

export async function registrarVentaEnServidor(
  token: string,
  venta: RegistrarVentaBody,
): Promise<RegistrarVentaServidorResult> {
  const res = await fetch(`${API_CONFIG.BASE_URL}/caja/ventas/registrar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(venta),
  });

  const data = (await res.json()) as { message?: string; detail?: string };
  if (!res.ok) {
    return {
      ok: false,
      status: res.status,
      detail: data.detail || data.message || res.statusText,
    };
  }

  return {
    ok: true,
    message: data.message || "Venta registrada correctamente.",
  };
}

export async function finalizarVentaOfflineLocal(params: {
  idEmpresa: number;
  idSesionCaja: number;
  payload: VentaPendientePayload;
}): Promise<RegistrarVentaResult> {
  const meta = await getOfflineMeta(params.idEmpresa);
  const row = await guardarVentaPendiente({
    idEmpresa: params.idEmpresa,
    idSesionCaja: params.idSesionCaja,
    snapshotVersion: meta?.catalogo_version ?? 0,
    payload: params.payload,
  });

  imprimirComprobanteOffline(params.payload, row.id_local);

  return {
    mode: "offline",
    id_local: row.id_local,
    message: "Venta guardada localmente. Se sincronizará al reconectar.",
  };
}

export async function sincronizarVentasPendientes(
  token: string,
  idEmpresa: number,
): Promise<{ sincronizados: number; errores: number }> {
  const tieneServidor = await pingServidor(token);
  if (!tieneServidor) {
    return { sincronizados: 0, errores: 0 };
  }

  const pendientes = await offlineDb.ventas_pendientes
    .where("id_empresa")
    .equals(idEmpresa)
    .filter((row) => ESTADOS_REINTENTABLES.includes(row.estado))
    .sortBy("created_at");

  let sincronizados = 0;
  let errores = 0;

  for (const row of pendientes) {
    let payload: VentaPendientePayload;
    try {
      payload = JSON.parse(row.payload) as VentaPendientePayload;
    } catch {
      await offlineDb.ventas_pendientes.update(row.id_local, {
        estado: "error",
        conflicto_motivo: "Payload local inválido",
      });
      errores += 1;
      continue;
    }

    await offlineDb.ventas_pendientes.update(row.id_local, { estado: "sincronizando" });

    try {
      const result = await registrarVentaEnServidor(token, payload.venta);
      if (result.ok) {
        await offlineDb.ventas_pendientes.update(row.id_local, {
          estado: "sincronizado",
          synced_at: new Date().toISOString(),
          conflicto_motivo: null,
          conflicto_unidades: null,
        });
        sincronizados += 1;
        continue;
      }

      await offlineDb.ventas_pendientes.update(row.id_local, {
        estado: "error",
        conflicto_motivo: result.detail,
      });
      errores += 1;
    } catch (error) {
      await offlineDb.ventas_pendientes.update(row.id_local, { estado: "pendiente" });
      if (esErrorDeRed(error)) break;
      errores += 1;
    }
  }

  return { sincronizados, errores };
}

export async function intentarRegistrarVenta(params: {
  token: string;
  idEmpresa: number;
  offlineHabilitado: boolean;
  idSesionCaja: number | null;
  payload: VentaPendientePayload;
  tipoComprobante: string;
}): Promise<RegistrarVentaResult> {
  if (
    params.offlineHabilitado &&
    esFacturaOfflineNoPermitida(
      params.tipoComprobante,
      params.payload.venta.quiere_factura,
    )
  ) {
    throw new Error("La factura electrónica requiere conexión con el servidor.");
  }

  try {
    const result = await registrarVentaEnServidor(params.token, params.payload.venta);
    if (result.ok) {
      return { mode: "online", message: result.message };
    }
    throw new Error(result.detail);
  } catch (error) {
    if (!params.offlineHabilitado || !esErrorDeRed(error)) {
      if (error instanceof Error) throw error;
      throw new Error("No se pudo registrar la venta.");
    }

    const idSesion = await resolverIdSesionCajaLocal(
      params.idEmpresa,
      params.idSesionCaja,
    );
    if (!idSesion) {
      throw new Error(
        "Sin conexión y no hay sesión de caja local. Abrí la caja con internet antes de vender offline.",
      );
    }

    return finalizarVentaOfflineLocal({
      idEmpresa: params.idEmpresa,
      idSesionCaja: idSesion,
      payload: params.payload,
    });
  }
}
