// Tipos para el sistema de mesas

export interface Mesa {
  id: number;
  numero: number;
  capacidad: number;
  estado: 'LIBRE' | 'OCUPADA' | 'RESERVADA';
  activo: boolean;
  id_empresa: number;
  created_at?: string;
  updated_at?: string;
}

export interface MesaLog {
  id: number;
  id_mesa: number;
  estado_anterior: 'LIBRE' | 'OCUPADA' | 'RESERVADA' | null;
  estado_nuevo: 'LIBRE' | 'OCUPADA' | 'RESERVADA';
  activo_anterior: boolean | null;
  activo_nuevo: boolean;
  timestamp: string;
  id_usuario: number;
  mesa?: Mesa;
}

export interface ConsumoMesa {
  id: number;
  timestamp_inicio: string;
  timestamp_cierre?: string;
  total: number;
  estado: 'abierto' | 'cerrado' | 'facturado';
  id_mesa: number;
  id_usuario: number;
  id_empresa: number;
  mesa?: Mesa;
  detalles?: ConsumoMesaDetalle[];
}

export interface ConsumoMesaDetalle {
  id: number;
  cantidad: number;
  precio_unitario: number;
  descuento_aplicado: number;
  id_consumo_mesa: number;
  id_articulo: number;
  articulo?: Articulo;
  subtotal?: number;
}

export interface Articulo {
  id: number;
  descripcion: string;
  precio_venta: number;
  stock_actual: number;
  activo: boolean;
  // otros campos...
}

export interface TicketRequest {
  id_consumo_mesa: number;
  formato?: 'ticket' | 'comprobante';
}

export interface TicketResponse {
  mesa_numero: number;
  timestamp: string;
  detalles: Array<{
    articulo: string;
    cantidad: number;
    precio_unitario: number;
    subtotal: number;
    categoria?: string | null;
  }>;
  total: number;
}

// Formularios
export interface MesaCreate {
  numero: number;
  capacidad: number;
  activo?: boolean;
}

export interface MesaUpdate {
  numero?: number;
  capacidad?: number;
  estado?: 'LIBRE' | 'OCUPADA' | 'RESERVADA';
  activo?: boolean;
}

export interface ConsumoCreate {
  id_mesa: number;
  id_usuario: number;
  id_empresa: number;
}

export interface ConsumoDetalleCreate {
  id_articulo: number;
  cantidad: number;
  precio_unitario: number;
  descuento_aplicado?: number;
}
