export type TipoEsquemaEmpresa = "estandar" | "especial";

export type PanelEstadisticasSecciones = {
  kpis_periodo: boolean;
  cajas_abiertas: boolean;
  alertas_stock: boolean;
  alertas_diferencias_caja: boolean;
  top_productos: boolean;
  top_categorias: boolean;
  ranking_vendedores: boolean;
  medios_pago: boolean;
  por_establecimiento: boolean;
};

export type SeccionEstadisticasKey = keyof PanelEstadisticasSecciones;

export const SECCIONES_ESTADISTICAS_DEFAULT: PanelEstadisticasSecciones = {
  kpis_periodo: true,
  cajas_abiertas: true,
  alertas_stock: true,
  alertas_diferencias_caja: true,
  top_productos: true,
  top_categorias: true,
  ranking_vendedores: true,
  medios_pago: true,
  por_establecimiento: true,
};

export const SECCIONES_ESTADISTICAS_LABELS: Record<SeccionEstadisticasKey, string> = {
  kpis_periodo: "KPIs hoy / ayer / mes",
  cajas_abiertas: "Cajas abiertas",
  alertas_stock: "Alertas de stock",
  alertas_diferencias_caja: "Diferencias de caja",
  top_productos: "Top productos",
  top_categorias: "Top categorías",
  ranking_vendedores: "Ranking vendedoras",
  medios_pago: "Medios de pago",
  por_establecimiento: "Por establecimiento",
};

export type PerfilOperativoResuelto = {
  version?: number;
  plantilla_origen?: string | null;
  modo_especial: boolean;
  sincronizar_google_sheets: boolean;
  caja_solo_comprobante: boolean;
  caja_permitir_remito_presupuesto: boolean;
  factura_auto_mercado_pago: boolean;
  /** Si true: transferencia/POS disparan factura AFIP automática. */
  factura_auto_transferencia_pos: boolean;
  panel_estadisticas_caja: boolean;
  panel_estadisticas_secciones?: PanelEstadisticasSecciones;
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
  factura_auto_transferencia_pos: false,
  panel_estadisticas_caja: false,
  panel_estadisticas_secciones: { ...SECCIONES_ESTADISTICAS_DEFAULT },
  mesas_habilitado: false,
  bloquear_descuentos_cajero: false,
  balanza_auto_agregar: false,
  balanza_auto_facturar: false,
  cache_degradado: false,
  empresas_transferencia_ids: [],
};
