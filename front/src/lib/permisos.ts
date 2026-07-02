const ROLES_VENTA_SIN_DESCUENTO = new Set(["Cajero", "Vendedora"]);

/** La Esquina (35) y FULL24 (36). */
export const EMPRESAS_PANEL_ESTADISTICAS = new Set([35, 36]);

/** La Esquina (35) y FULL24 (36): en caja solo comprobante (sin factura/remito/presupuesto). */
export const EMPRESAS_SOLO_COMPROBANTE_CAJA = new Set([35, 36]);

export function empresaTienePanelEstadisticas(idEmpresa: number | undefined): boolean {
  if (!idEmpresa) return false;
  return EMPRESAS_PANEL_ESTADISTICAS.has(idEmpresa);
}

export function empresaSoloComprobanteCaja(idEmpresa: number | undefined): boolean {
  if (!idEmpresa) return false;
  return EMPRESAS_SOLO_COMPROBANTE_CAJA.has(idEmpresa);
}

export function empresaBloqueaDescuentosCajero(
  aclaraciones?: Record<string, string>,
): boolean {
  const valor = aclaraciones?.bloquear_descuentos_cajero ?? "false";
  return valor === "true" || valor === "1";
}

export function puedeAplicarDescuentos(
  rolNombre: string | undefined,
  aclaraciones?: Record<string, string>,
): boolean {
  if (!rolNombre) return false;
  if (!empresaBloqueaDescuentosCajero(aclaraciones)) return true;
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
