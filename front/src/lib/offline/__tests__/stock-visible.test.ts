import {
  agruparPendientesPorArticulo,
  calcularStockVisible,
} from "@/lib/offline/stock-visible";

describe("stock-visible", () => {
  it("resta ventas pendientes del snapshot", () => {
    expect(calcularStockVisible(24, 3)).toBe(21);
  });

  it("no deja stock visible negativo", () => {
    expect(calcularStockVisible(2, 5)).toBe(0);
  });

  it("agrupa pendientes por artículo", () => {
    expect(
      agruparPendientesPorArticulo([
        { id_articulo: "1", cantidad: 2 },
        { id_articulo: "1", cantidad: 1 },
        { id_articulo: "2", cantidad: 4 },
      ]),
    ).toEqual({ "1": 3, "2": 4 });
  });
});
