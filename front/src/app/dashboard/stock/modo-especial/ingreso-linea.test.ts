import { readFileSync } from "fs";
import { join } from "path";
import {
  agregarAlternativo,
  barrasCambiaron,
  precioVentaParaEnviar,
  precioVentaVisible,
  textoStock,
  esDestinoLocal,
  repartoLinea,
  textoDestinoIngreso,
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

  it("destino propio es el ingreso local", () => {
    expect(esDestinoLocal("")).toBe(true);
    expect(esDestinoLocal("local")).toBe(true);
    expect(esDestinoLocal("2")).toBe(false);
  });

  it("reparte 10 en 6 que quedan y 4 que se envían", () => {
    expect(repartoLinea(10, "4")).toEqual({ ok: true, queda: 6, enviar: 4 });
    expect(repartoLinea(10, "")).toEqual({ ok: true, queda: 10, enviar: 0 });
    expect(repartoLinea(10, "10")).toEqual({ ok: true, queda: 0, enviar: 10 });
    expect(repartoLinea(10, "11").ok).toBe(false);
  });

  it("explica el reparto y que el envío queda pendiente de recepción", () => {
    expect(textoDestinoIngreso(null)).toMatch(/todo se queda en esta sucursal/);
    expect(textoDestinoIngreso("Sucursal Norte")).toMatch(/pendiente de recepción/);
    expect(textoDestinoIngreso("Sucursal Norte")).toMatch(/Sucursal Norte/);
  });

  it("el registro del ingreso no toca ventas_pendientes ni limpia la empresa offline", () => {
    const src = readFileSync(join(__dirname, "ModoEspecialView.tsx"), "utf8");
    const inicio = src.indexOf("const registrarIngreso");
    const fin = src.indexOf("const abrirTransferencia");
    const funcion = src.slice(inicio, fin);
    expect(inicio).toBeGreaterThan(-1);
    expect(funcion).toContain("ingresarStockModoEspecial");
    expect(funcion).not.toContain("ventas_pendientes");
    expect(funcion).not.toContain("clearOfflineEmpresa");
    expect(src).not.toContain("clearOfflineEmpresa");
  });
});