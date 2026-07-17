export type TipoEsquemaEmpresa = "estandar" | "especial";

export type PerfilOperativoResuelto = {
  version?: number;
  plantilla_origen?: string | null;
  modo_especial: boolean;
  sincronizar_google_sheets: boolean;
  caja_solo_comprobante: boolean;
  caja_permitir_remito_presupuesto: boolean;
  factura_auto_mercado_pago: boolean;
  panel_estadisticas_caja: boolean;
  mesas_habilitado: boolean;
  bloquear_descuentos_cajero: boolean;
  balanza_auto_agregar: boolean;
  balanza_auto_facturar: boolean;
  cache_degradado: boolean;
  empresas_transferencia_ids: number[];
  casos_especiales?: Record<string, string | number | boolean>;
  facturacion_afip_habilitada?: boolean;
  caja_puede_facturar?: boolean;
  caja_puede_remito_presupuesto?: boolean;
};

export const PERFIL_ESTANDAR_DEFAULT: PerfilOperativoResuelto = {
  modo_especial: false,
  sincronizar_google_sheets: true,
  caja_solo_comprobante: false,
  caja_permitir_remito_presupuesto: false,
  factura_auto_mercado_pago: false,
  panel_estadisticas_caja: false,
  mesas_habilitado: false,
  bloquear_descuentos_cajero: false,
  balanza_auto_agregar: false,
  balanza_auto_facturar: false,
  cache_degradado: false,
  empresas_transferencia_ids: [],
};
