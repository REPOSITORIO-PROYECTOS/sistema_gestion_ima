import {
  agregarAlternativo,
  barrasCambiaron,
  precioVentaParaEnviar,
  precioVentaVisible,
  textoStock,
  unirCodigos,
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

  it("agrega alternativos con Enter y rechaza duplicados", () => {
    const primero = agregarAlternativo("7790001000011", [], "7790001000099");
    expect(primero).toEqual({ ok: true, alternativos: ["7790001000099"] });
    if (!primero.ok) return;
    const segundo = agregarAlternativo("7790001000011", primero.alternativos, "7790001000088");
    expect(segundo).toEqual({ ok: true, alternativos: ["7790001000099", "7790001000088"] });
    expect(agregarAlternativo("7790001000011", primero.alternativos, "7790001000011").ok).toBe(false);
    expect(agregarAlternativo("7790001000011", primero.alternativos, "7790001000099").ok).toBe(false);
    expect(agregarAlternativo("7790001000011", primero.alternativos, "  ").ok).toBe(false);
  });

  it("guarda el principal primero y no repite alternativos", () => {
    expect(unirCodigos("7790001000011", ["7790001000099", "7790001000011"])).toEqual([
      "7790001000011",
      "7790001000099",
    ]);
  });
});