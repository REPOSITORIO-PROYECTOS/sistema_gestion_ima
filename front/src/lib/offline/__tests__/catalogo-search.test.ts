import {
  buscarArticulosLocal,
  buscarPorCodigoLocal,
} from "@/lib/offline/catalogo-search";
import { offlineDb, type OfflineArticulo } from "@/lib/offline/db";
import { obtenerCantidadesPendientesPorArticulo } from "@/lib/offline/venta-offline";

jest.mock("@/lib/offline/db", () => ({
  offlineDb: {
    articulos: {
      where: jest.fn(),
      get: jest.fn(),
    },
    codigos_barras: {
      get: jest.fn(),
    },
  },
}));

jest.mock("@/lib/offline/venta-offline", () => ({
  obtenerCantidadesPendientesPorArticulo: jest.fn().mockResolvedValue({}),
}));

const articuloYerba: OfflineArticulo = {
  id: "1",
  id_empresa: 37,
  descripcion: "Yerba mate 500g",
  precio_venta: 3500,
  venta_negocio: 3300,
  stock_actual: 24,
  stock_snapshot: 24,
  unidad_venta: "unidad",
  precio_manual: false,
  activo: true,
  codigo_interno: "LOC-001",
};

describe("catalogo-search", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("busca artículos locales por descripción", async () => {
    jest.mocked(offlineDb.articulos.where).mockReturnValue({
      equals: jest.fn().mockReturnValue({
        toArray: jest.fn().mockResolvedValue([articuloYerba]),
      }),
    } as never);

    const resultados = await buscarArticulosLocal(37, "yerba", 10);

    expect(resultados).toEqual([
      {
        id: "1",
        nombre: "Yerba mate 500g",
        precio_venta: 3500,
        venta_negocio: 3300,
        stock_actual: 24,
        unidad_venta: "unidad",
        precio_manual: false,
      },
    ]);
  });

  it("muestra stock_snapshot aunque stock_actual en IndexedDB sea distinto", async () => {
    const articuloStockDesfasado: OfflineArticulo = {
      ...articuloYerba,
      stock_actual: 5,
      stock_snapshot: 18,
    };
    jest.mocked(offlineDb.articulos.where).mockReturnValue({
      equals: jest.fn().mockReturnValue({
        toArray: jest.fn().mockResolvedValue([articuloStockDesfasado]),
      }),
    } as never);

    const resultados = await buscarArticulosLocal(37, "yerba", 10);

    expect(resultados[0]?.stock_actual).toBe(18);
  });

  it("busca artículos locales por código de barras", async () => {
    jest.mocked(offlineDb.codigos_barras.get).mockResolvedValue({
      codigo: "7790001000011",
      id_articulo: "1",
      id_empresa: 37,
    });
    jest.mocked(offlineDb.articulos.get).mockResolvedValue(articuloYerba);

    const resultado = await buscarPorCodigoLocal(37, "7790001000011");

    expect(resultado?.id).toBe("1");
    expect(resultado?.nombre).toBe("Yerba mate 500g");
  });
});
