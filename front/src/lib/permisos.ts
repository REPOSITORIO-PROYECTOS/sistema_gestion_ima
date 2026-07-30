import type {
  PanelEstadisticasSecciones,
  PerfilOperativoResuelto,
  SeccionEstadisticasKey,
} from "@/types/perfilOperativo";
import { SECCIONES_ESTADISTICAS_DEFAULT } from "@/types/perfilOperativo";

const ROLES_VENTA_SIN_DESCUENTO = new Set(["Cajero", "Vendedora"]);

export function empresaTienePanelEstadisticas(
  perfil?: PerfilOperativoResuelto | null,
): boolean {
  return Boolean(perfil?.panel_estadisticas_caja);
}

export function seccionesEstadisticasResueltas(
  perfil?: PerfilOperativoResuelto | null,
): PanelEstadisticasSecciones {
  return {
    ...SECCIONES_ESTADISTICAS_DEFAULT,
    ...(perfil?.panel_estadisticas_secciones ?? {}),
  };
}

export function seccionEstadisticasVisible(
  perfil: PerfilOperativoResuelto | null | undefined,
  key: SeccionEstadisticasKey,
): boolean {
  if (!empresaTienePanelEstadisticas(perfil)) return false;
  return Boolean(seccionesEstadisticasResueltas(perfil)[key]);
}

export function empresaSoloComprobanteCaja(
  perfil?: PerfilOperativoResuelto | null,
): boolean {
  return Boolean(perfil?.caja_solo_comprobante);
}

/** Empresa con autofactura AFIP al pagar transferencia o POS. */
export function empresaAutofacturaTransferenciaPos(
  perfil?: PerfilOperativoResuelto | null,
): boolean {
  return (
    Boolean(perfil?.factura_auto_transferencia_pos) &&
    Boolean(perfil?.caja_puede_facturar)
  );
}

const METODOS_AUTOFACTURA = new Set(["transferencia", "bancario", "pos"]);

export function metodoDisparaAutofacturaTransferenciaPos(metodo?: string | null): boolean {
  if (!metodo) return false;
  return METODOS_AUTOFACTURA.has(metodo.trim().toLowerCase());
}

export function pagosDisparanAutofacturaTransferenciaPos(
  metodoUnico?: string | null,
  pagosMultiples?: Array<{ metodo_pago: string }> | null,
): boolean {
  if (pagosMultiples && pagosMultiples.length > 0) {
    return pagosMultiples.some((p) => metodoDisparaAutofacturaTransferenciaPos(p.metodo_pago));
  }
  return metodoDisparaAutofacturaTransferenciaPos(metodoUnico);
}

export function empresaModoEspecial(perfil?: PerfilOperativoResuelto | null): boolean {
  return Boolean(perfil?.modo_especial);
}

export function empresaBloqueaDescuentosCajero(
  perfil?: PerfilOperativoResuelto | null,
  aclaraciones?: Record<string, string>,
): boolean {
  if (perfil?.bloquear_descuentos_cajero) return true;
  const valor = aclaraciones?.bloquear_descuentos_cajero ?? "false";
  return valor === "true" || valor === "1";
}

export function puedeAplicarDescuentos(
  rolNombre: string | undefined,
  perfil?: PerfilOperativoResuelto | null,
  aclaraciones?: Record<string, string>,
): boolean {
  if (!rolNombre) return false;
  if (!empresaBloqueaDescuentosCajero(perfil, aclaraciones)) return true;
  return !ROLES_VENTA_SIN_DESCUENTO.has(rolNombre);
}

export function puedeGestionarUsuarios(rolNombre: string | undefined): boolean {
  return rolNombre === "Admin" || rolNombre === "Gerente" || rolNombre === "Soporte";
}

export function puedeEditarCredenciales(rolNombre: string | undefined): boolean {
  return rolNombre === "Admin" || rolNombre === "Gerente" || rolNombre === "Soporte";
}

/** Admin, Gerente y Encargada pueden modificar su propio usuario desde el panel. */
export function puedeModificarCredencialesPropias(rolNombre: string | undefined): boolean {
  return rolNombre === "Admin" || rolNombre === "Gerente" || rolNombre === "Encargada";
}

export function puedeEditarCatalogo(rolNombre: string | undefined): boolean {
  return rolNombre === "Admin" || rolNombre === "Gerente" || rolNombre === "Encargada";
}

export function puedeVerPanelEstadisticas(rolNombre: string | undefined): boolean {
  return (
    rolNombre === "Admin" ||
    rolNombre === "Gerente" ||
    rolNombre === "Encargada" ||
    rolNombre === "Soporte"
  );
}
