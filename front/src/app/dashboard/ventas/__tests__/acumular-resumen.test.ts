import { acumularEnResumen, type LineaResumen } from "../acumular-resumen";

function linea(parcial: Partial<LineaResumen> & Pick<LineaResumen, "cantidad" | "precioBase">): LineaResumen {
  return {
    id: "1",
    tipo: "Yerba",
    precioTotal: parcial.precioBase,
    descuentoAplicado: false,
    porcentajeDescuento: 0,
    descuentoNominal: 0,
    ...parcial,
  };
}

describe("acumular en el resumen de la caja", () => {
  it("suma cantidad del mismo artículo aunque el nombre venga de otro escaneo", () => {
    const primero = linea({ id: "10", tipo: "Yerba", cantidad: 1, precioBase: 6200 });
    const porAlternativo = linea({ id: "10", tipo: "Yerba mate 500g", cantidad: 1, precioBase: 6200 });
    const resumen = acumularEnResumen([primero], porAlternativo);
    expect(resumen).toHaveLength(1);
    expect(resumen[0].cantidad).toBe(2);
    expect(resumen[0].precioBase).toBe(12400);
    expect(resumen[0].tipo).toBe("Yerba");
  });

  it("suma el peso de un pesable con el mismo precio por unidad", () => {
    const primero = linea({ id: "5", tipo: "Queso", cantidad: 0.25, precioBase: 250 });
    const otraPesada = linea({ id: "5", tipo: "Queso", cantidad: 0.5, precioBase: 500 });
    const resumen = acumularEnResumen([primero], otraPesada);
    expect(resumen).toHaveLength(1);
    expect(resumen[0].cantidad).toBe(0.75);
    expect(resumen[0].precioBase).toBe(750);
  });

  it("no mezcla un precio unitario distinto ni un descuento ya cargado", () => {
    const manual = linea({ id: "10", cantidad: 1, precioBase: 5000 });
    const catalogo = linea({ id: "10", cantidad: 1, precioBase: 6200 });
    expect(acumularEnResumen([manual], catalogo)).toHaveLength(2);

    const conDescuento = linea({
      id: "10",
      cantidad: 1,
      precioBase: 6200,
      precioTotal: 5580,
      descuentoAplicado: true,
      porcentajeDescuento: 10,
    });
    const otra = linea({ id: "10", cantidad: 1, precioBase: 6200 });
    expect(acumularEnResumen([conDescuento], otra)).toHaveLength(2);
  });

  it("no acumula un escaneo sin id de artículo", () => {
    const suelto = linea({ id: undefined, tipo: "Balanza", cantidad: 0.4, precioBase: 400 });
    const otro = linea({ id: undefined, tipo: "Balanza", cantidad: 0.4, precioBase: 400 });
    expect(acumularEnResumen([suelto], otro)).toHaveLength(2);
  });
});
