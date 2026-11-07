import {
  aplicarPrecioVigente,
  actualizarTodasLasLineas,
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

  it("por defecto no pisa un producto de precio manual", () => {
    const actualizada = aplicarPrecioVigente(
      linea,
      { precio_venta: 9999, precio_manual: true },
      "0",
    );

    expect(actualizada.precioBase).toBe(2000);
    expect(actualizada.precioTotal).toBe(2000);
  });

  it("con forzarManual sí actualiza precio manual", () => {
    const actualizada = aplicarPrecioVigente(
      linea,
      { precio_venta: 1800, precio_manual: true },
      "0",
      { forzarManual: true },
    );

    expect(actualizada.precioBase).toBe(3600);
    expect(actualizada.precioTotal).toBe(3600);
  });

  it("actualiza todas las líneas del resumen", () => {
    const lineas: LineaCaja[] = [
      { ...linea, id: "1", precioBase: 100, precioTotal: 100, cantidad: 1 },
      { ...linea, id: "2", precioBase: 200, precioTotal: 200, cantidad: 1 },
      { ...linea, id: undefined, tipo: "Sin id", precioBase: 50, precioTotal: 50, cantidad: 1 },
    ];
    const precios = new Map([
      ["1", { precio_venta: 500, venta_negocio: 400 }],
      ["2", { precio_venta: 800, venta_negocio: 700, precio_manual: true }],
    ]);

    const resultado = actualizarTodasLasLineas(lineas, precios, "0");

    expect(resultado.actualizadas).toBe(2);
    expect(resultado.sinPrecio).toBe(1);
    expect(resultado.lineas[0].precioTotal).toBe(500);
    expect(resultado.lineas[1].precioTotal).toBe(800);
    expect(resultado.lineas[2].precioTotal).toBe(50);
  });
});
