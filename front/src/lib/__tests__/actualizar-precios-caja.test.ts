import {
  aplicarPrecioVigente,
  precioSegunCliente,
  type LineaCaja,
} from "../actualizar-precios-caja";

const linea: LineaCaja = {
  id: "10",
  tipo: "Yerba",
  cantidad: 2,
  precioBase: 2000,
  precioTotal: 2000,
  porcentajeDescuento: 0,
  descuentoNominal: 0,
};

describe("actualizar precios de la caja", () => {
  it("cliente final toma precio de venta", () => {
    expect(
      precioSegunCliente({ precio_venta: 1500, venta_negocio: 1200 }, "0"),
    ).toBe(1500);
  });

  it("cliente registrado toma precio de negocio", () => {
    expect(
      precioSegunCliente({ precio_venta: 1500, venta_negocio: 1200 }, "1"),
    ).toBe(1200);
  });

  it("recalcula la línea y conserva un descuento ya cargado", () => {
    const actualizada = aplicarPrecioVigente(
      { ...linea, porcentajeDescuento: 10, descuentoNominal: 50 },
      { precio_venta: 1500, venta_negocio: 1200 },
      "0",
    );

    expect(actualizada.cantidad).toBe(2);
    expect(actualizada.precioBase).toBe(3000);
    expect(actualizada.precioTotal).toBe(2650);
    expect(actualizada.porcentajeDescuento).toBe(10);
  });

  it("no pisa un producto de precio manual", () => {
    const actualizada = aplicarPrecioVigente(
      linea,
      { precio_venta: 9999, precio_manual: true },
      "0",
    );

    expect(actualizada.precioBase).toBe(2000);
    expect(actualizada.precioTotal).toBe(2000);
  });
});
