import {
  buildResumenCierreOfflineTexto,
  esErrorDeRed,
  formatoMonedaAr,
} from "@/lib/offline/cierre-caja";

describe("cierre-caja offline", () => {
  it("detecta errores de red", () => {
    expect(esErrorDeRed(new TypeError("Failed to fetch"))).toBe(true);
    expect(esErrorDeRed(new Error("network down"))).toBe(true);
    expect(esErrorDeRed(new Error("caja cerrada"))).toBe(false);
  });

  it("formatea montos en ARS", () => {
    expect(formatoMonedaAr(1500.5)).toMatch(/1\.500,50|1500,50/);
  });

  it("arma resumen de cierre offline con saldos", () => {
    const texto = buildResumenCierreOfflineTexto(
      {
        id_sesion_caja: 42,
        saldo_final_declarado: 10000,
        saldo_final_efectivo: 5000,
        saldo_final_transferencias: 3000,
        saldo_final_bancario: 2000,
        nombre_usuario: "cajero1",
      },
      "Kiosco Demo",
    );

    expect(texto).toContain("CIERRE DE CAJA (OFFLINE)");
    expect(texto).toContain("Kiosco Demo");
    expect(texto).toContain("Sesión: 42");
    expect(texto).toContain("cajero1");
    expect(texto).toContain("Pendiente de sincronizar");
  });
});
