// types/contabilidad.types.ts

// CAMBIO: Creamos una interfaz específica para los datos de la factura
export interface DatosFactura {
  cae: string;
  comprobante_numero: string;
  fecha_vencimiento_cae?: string; // Opcional por si no siempre viene
  // Puedes añadir aquí otros campos que esperes de la AFIP
}

interface InfoCliente {
  id: number;
  nombre_razon_social: string;
}

interface InfoVenta {
  id: number;
  facturada: boolean;
  // CAMBIO: Usamos nuestra nueva interfaz en lugar de un objeto con 'any'
  datos_factura: DatosFactura | null;
  cliente: InfoCliente | null;
}

export interface MovimientoContable {
  id: number;
  timestamp: string;
  tipo: "INGRESO" | "EGRESO" | "VENTA";
  concepto: string;
  monto: number;
  metodo_pago: string | null;
  venta: InfoVenta | null;  
}