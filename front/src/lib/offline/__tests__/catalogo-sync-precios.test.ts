import "fake-indexeddb/auto";
import { offlineDb } from "../db";
import { limpiarCatalogoVigente, aplicarPreciosVigentesABusqueda } from "../catalogo-vigente";
import {
  ejecutarActualizacionPrecios,
  mensajeToastActualizacion,
} from "../actualizar-precios-flujo";
import type { LineaCaja } from "../../actualizar-precios-caja";

const EMPRESA = 39;

const lineaVieja: LineaCaja = {
  id: "10",
  tipo: "Yerba",
  cantidad: 2,
  precioBase: 200,
  precioTotal: 200,
  porcentajeDescuento: 0,
  descuentoNominal: 0,
};

const articuloServidor = {
  id: 10,
  descripcion: "Yerba",
  precio_venta: 250,
  venta_negocio: 200,
  stock_actual: 4,
  unidad_venta: "unidad",
  precio_manual: false,
  activo: true,
  codigo_interno: "Y1",
  codigos: [{ codigo: "779000" }],
};

const payloadPendiente = JSON.stringify({
  venta: { total_venta: 100, articulos_vendidos: [{ id_articulo: "10", cantidad: 1 }] },
});

function respuestaJson(body: unknown, status = 200): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

async function sembrarCacheVieja(): Promise<void> {
  await offlineDb.articulos.put({
    id: "10",
    id_empresa: EMPRESA,
    descripcion: "Yerba",
    precio_venta: 100,
    venta_negocio: 80,
    stock_actual: 4,
    stock_snapshot: 4,
    unidad_venta: "unidad",
    precio_manual: false,
    activo: true,
    codigo_interno: "Y1",
  });
  await offlineDb.ventas_pendientes.put({
    id_local: "venta_test_1",
    id_empresa: EMPRESA,
    estado: "pendiente",
    payload: payloadPendiente,
    snapshot_version: 1,
    id_sesion_caja_cache: 7,
    created_at: "2026-11-05T15:00:00.000Z",
    synced_at: null,
  });
  await offlineDb.cierres_pendientes.put({
    id_local: "cierre_test_1",
    id_empresa: EMPRESA,
    payload: JSON.stringify({ id_sesion_caja: 7 }),
    created_at: "2026-11-05T18:00:00.000Z",
    synced_at: null,
  });
}

describe("actualización de precios de la caja", () => {
  beforeEach(async () => {
    limpiarCatalogoVigente();
    await offlineDb.articulos.clear();
    await offlineDb.codigos_barras.clear();
    await offlineDb.meta.clear();
    await offlineDb.ventas_pendientes.clear();
    await offlineDb.cierres_pendientes.clear();
    await sembrarCacheVieja();
  });

  it("pisa caché, resumen y búsqueda, y deja las ventas pendientes intactas", async () => {
    const fetchMock = jest.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/articulos/version")) {
        return respuestaJson({ version: 4, total: 1 });
      }
      if (url.includes("/articulos/obtener_todos")) {
        expect(url).toContain("orden=id");
        return respuestaJson([articuloServidor]);
      }
      throw new Error(`URL inesperada ${url}`);
    });
    global.fetch = fetchMock as typeof fetch;

    const [primera, segunda] = await Promise.all([
      ejecutarActualizacionPrecios({
        token: "token",
        idEmpresa: EMPRESA,
        hayConexion: () => true,
        lineas: [lineaVieja],
        tipoClienteId: "0",
      }),
      ejecutarActualizacionPrecios({
        token: "token",
        idEmpresa: EMPRESA,
        hayConexion: () => true,
        lineas: [lineaVieja],
        tipoClienteId: "0",
      }),
    ]);

    expect(primera.ok).toBe(true);
    expect(segunda.ok).toBe(true);
    if (!primera.ok || !segunda.ok) return;

    expect(primera.lineas[0].precioBase).toBe(500);
    expect(primera.lineas[0].precioTotal).toBe(500);
    expect(mensajeToastActualizacion(primera).tipo).toBe("success");

    const guardado = await offlineDb.articulos.get("10");
    expect(guardado?.precio_venta).toBe(250);
    expect(guardado?.venta_negocio).toBe(200);

    const busqueda = aplicarPreciosVigentesABusqueda(EMPRESA, [
      {
        id: "10",
        precio_venta: 100,
        venta_negocio: 80,
        precio_manual: false,
      },
    ]);
    expect(busqueda[0].precio_venta).toBe(250);

    const pendiente = await offlineDb.ventas_pendientes.get("venta_test_1");
    expect(pendiente?.payload).toBe(payloadPendiente);
    expect(pendiente?.estado).toBe("pendiente");
    const cierre = await offlineDb.cierres_pendientes.get("cierre_test_1");
    expect(cierre?.payload).toContain("7");

    const paginas = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes("/articulos/obtener_todos"),
    );
    expect(paginas).toHaveLength(1);
  });

  it("sin red no toca la caché y el aviso no es de éxito", async () => {
    global.fetch = jest.fn();

    const resultado = await ejecutarActualizacionPrecios({
      token: "token",
      idEmpresa: EMPRESA,
      hayConexion: () => false,
      lineas: [lineaVieja],
      tipoClienteId: "0",
    });

    expect(resultado.ok).toBe(false);
    expect(mensajeToastActualizacion(resultado)).toEqual({
      tipo: "error",
      texto: "Sin conexión no pude actualizar los precios.",
    });
    expect(global.fetch).not.toHaveBeenCalled();
    expect((await offlineDb.articulos.get("10"))?.precio_venta).toBe(100);
    expect((await offlineDb.ventas_pendientes.get("venta_test_1"))?.payload).toBe(payloadPendiente);
  });

  it("si la bajada no completa, conserva la caché y no avisa éxito", async () => {
    global.fetch = jest.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/articulos/version")) {
        return respuestaJson({ version: 9, total: 2 });
      }
      if (url.includes("/articulos/obtener_todos")) {
        return respuestaJson([articuloServidor]);
      }
      throw new Error(`URL inesperada ${url}`);
    }) as typeof fetch;

    const resultado = await ejecutarActualizacionPrecios({
      token: "token",
      idEmpresa: EMPRESA,
      hayConexion: () => true,
      lineas: [lineaVieja],
      tipoClienteId: "0",
      opcionesDescarga: { limit: 1, timeoutMs: 1000 },
    });

    expect(resultado.ok).toBe(false);
    expect(mensajeToastActualizacion(resultado).tipo).toBe("error");
    expect(mensajeToastActualizacion(resultado).texto).not.toMatch(/Actualicé/);
    expect((await offlineDb.articulos.get("10"))?.precio_venta).toBe(100);
    expect(await offlineDb.articulos.count()).toBe(1);
    expect((await offlineDb.ventas_pendientes.get("venta_test_1"))?.payload).toBe(payloadPendiente);
    expect((await offlineDb.meta.toArray())).toHaveLength(0);
  });

  it("si una página se corta por tiempo, no reemplaza la caché", async () => {
    global.fetch = jest.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          const error = new Error("aborted");
          error.name = "AbortError";
          reject(error);
        });
      });
    }) as typeof fetch;

    const resultado = await ejecutarActualizacionPrecios({
      token: "token",
      idEmpresa: EMPRESA,
      hayConexion: () => true,
      lineas: [lineaVieja],
      tipoClienteId: "0",
      opcionesDescarga: { timeoutMs: 30 },
    });

    expect(resultado.ok).toBe(false);
    expect(mensajeToastActualizacion(resultado).tipo).toBe("error");
    expect((await offlineDb.articulos.get("10"))?.precio_venta).toBe(100);
    expect((await offlineDb.ventas_pendientes.get("venta_test_1"))?.estado).toBe("pendiente");
  });
});
