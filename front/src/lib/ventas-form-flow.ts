import type { KeyboardEvent } from "react";

/** IDs de campos del flujo de caja (Enter avanza entre ellos). */
export const VENTAS_CAMPOS = {
  producto: "codigo-barras",
  cantidadUnidad: "cantidad-unidad",
  cantidadGranel: "cantidad-granel",
  precioGranel: "precio-granel",
  precioManual: "precio-manual",
  agregar: "btn-agregar-producto",
  finalizar: "btn-finalizar-compra",
  montoEfectivo: "input-monto-efectivo",
  registrar: "btn-registrar-venta",
} as const;

export function focusVentasCampo(
  id: keyof typeof VENTAS_CAMPOS | (typeof VENTAS_CAMPOS)[keyof typeof VENTAS_CAMPOS],
): void {
  const elementId = id in VENTAS_CAMPOS ? VENTAS_CAMPOS[id as keyof typeof VENTAS_CAMPOS] : id;
  window.setTimeout(() => {
    const el = document.getElementById(elementId);
    if (el && typeof el.focus === "function") {
      el.focus();
      if (el instanceof HTMLInputElement) {
        el.select();
      }
    }
  }, 50);
}

export function handleEnterAvanzar(
  e: KeyboardEvent,
  onAvanzar: () => void,
): void {
  if (e.key !== "Enter") return;
  e.preventDefault();
  onAvanzar();
}

/** Comprobante simple (recibo) vs factura fiscal — flujo básico de caja. */
export const TIPOS_COMPROBANTE_RAPIDO = ["recibo", "factura"] as const;
export type TipoComprobanteRapido = (typeof TIPOS_COMPROBANTE_RAPIDO)[number];

export const TIPO_COMPROBANTE_DEFAULT: TipoComprobanteRapido = "recibo";

export function tipoComprobanteDesdeFlecha(
  key: string,
): TipoComprobanteRapido | null {
  if (key === "ArrowLeft") return "recibo";
  if (key === "ArrowRight") return "factura";
  return null;
}

export function esTipoComprobanteRecibo(tipo: string): boolean {
  return tipo === "recibo" || tipo === "comprobante";
}
