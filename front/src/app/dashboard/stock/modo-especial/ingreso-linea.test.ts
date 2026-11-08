import {
  barrasCambiaron,
  precioVentaParaEnviar,
  precioVentaVisible,
  textoStock,
} from "./ingreso-linea";

describe("ingreso masivo", () => {
  it("muestra el stock aunque sea cero", () => {
    expect(textoStock(0)).toBe("stk 0");
    expect(textoStock(23)).toBe("stk 23");
  });

  it("autocompleta el precio de venta y no lo descarta", () => {
    expect(precioVentaVisible({ precio_venta: 6200 })).toBe("6200");
    expect(precioVentaVisible({ precio_venta: 0 })).toBe("0");
  });

  it("no envía el precio si el usuario no lo cambió", () => {
    expect(precioVentaParaEnviar("6200", "6200")).toBeUndefined();
    expect(precioVentaParaEnviar("6200", "6200.000")).toBeUndefined();
    expect(precioVentaParaEnviar("6200", "")).toBeUndefined();
  });

  it("envía el precio solo cuando fue modificado", () => {
    expect(precioVentaParaEnviar("6200", "7100")).toBe(7100);
    expect(precioVentaParaEnviar("6200", "0")).toBe(0);
  });

  it("detecta un código de barras editado", () => {
    expect(barrasCambiaron("7790001000011", "7790001000011")).toBe(false);
    expect(barrasCambiaron("7790001000011", "7790001000099")).toBe(true);
    expect(barrasCambiaron("7790001000011", "")).toBe(true);
  });
});