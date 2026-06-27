const ROLES_VENTA_SIN_DESCUENTO = new Set(["Cajero", "Vendedora"]);

/** La Esquina (35) y FULL24 (36). */
export const EMPRESAS_PANEL_ESTADISTICAS = new Set([35, 36]);

export function empresaTienePanelEstadisticas(idEmpresa: number | undefined): boolean {
  if (!idEmpresa) return false;
  return EMPRESAS_PANEL_ESTADISTICAS.has(idEmpresa);
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
  return rolNombre === "Admin" || rolNombre === "Soporte";
}

export function puedeEditarCredenciales(rolNombre: string | undefined): boolean {
  return rolNombre === "Admin" || rolNombre === "Soporte";
}

export function puedeVerPanelEstadisticas(rolNombre: string | undefined): boolean {
  return (
    rolNombre === "Admin" ||
    rolNombre === "Gerente" ||
    rolNombre === "Encargada" ||
    rolNombre === "Soporte"
  );
}
