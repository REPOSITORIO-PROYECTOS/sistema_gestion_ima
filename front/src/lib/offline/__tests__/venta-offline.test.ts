import {
  buildComprobanteOfflineTexto,
  esFacturaOfflineNoPermitida,
} from "@/lib/offline/venta-offline";
import type { VentaPendientePayload } from "@/lib/offline/venta-offline";

const payloadBase: VentaPendientePayload = {
  venta: {
    id_cliente: 0,
    total_venta: 1500,
    descuento_total: 0,
    paga_con: 2000,
    pago_separado: false,
    detalles_pago_separado: "",
    tipo_comprobante_solicitado: "recibo",
    quiere_factura: false,
    metodo_pago: "EFECTIVO",
    articulos_vendidos: [
      {
        id_articulo: 2,
        nombre: "Yerba mate 500g",
        cantidad: 2,
        precio_unitario: 750,
        subtotal: 1500,
      },
    ],
  },
  meta: {
    tipo_comprobante: "recibo",
    observaciones: "",
    total_final: 1500,
    descuento_nominal_total: 0,
    descuento_sobre_total: 0,
    cliente_nombre: "Consumidor Final",
    cuit_receptor: "0",
    empresa_nombre: "Kiosco Demo",
  },
};

describe("venta-offline", () => {
  it("bloquea factura offline", () => {
    expect(esFacturaOfflineNoPermitida("factura", true)).toBe(true);
    expect(esFacturaOfflineNoPermitida("recibo", false)).toBe(false);
    expect(esFacturaOfflineNoPermitida("factura_b", false)).toBe(true);
  });

  it("arma comprobante offline con items y referencia local", () => {
    const texto = buildComprobanteOfflineTexto(payloadBase, "venta_local_1");
    expect(texto).toContain("COMPROBANTE RECIBO (OFFLINE)");
    expect(texto).toContain("Yerba mate 500g");
    expect(texto).toContain("Kiosco Demo");
    expect(texto).toContain("venta_local_1");
    expect(texto).toContain("Pendiente de sincronizar");
  });
});
