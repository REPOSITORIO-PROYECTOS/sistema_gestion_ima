import { useCajaStore } from "@/lib/cajaStore";
import { getOfflineMeta, upsertOfflineMeta } from "@/lib/offline/db";

jest.mock("@/lib/offline/db", () => ({
  getOfflineMeta: jest.fn(),
  upsertOfflineMeta: jest.fn(),
}));

const mockedGetOfflineMeta = jest.mocked(getOfflineMeta);
const mockedUpsertOfflineMeta = jest.mocked(upsertOfflineMeta);

describe("useCajaStore offline degradado", () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => undefined);
    mockedGetOfflineMeta.mockReset();
    mockedUpsertOfflineMeta.mockReset();
    useCajaStore.setState({
      cajaAbierta: false,
      idSesion: null,
      modoOfflineCaja: false,
      estadoVerificado: false,
    });
    global.fetch = jest.fn();
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it("mantiene la caja abierta desde meta local si el servidor no responde", async () => {
    mockedGetOfflineMeta.mockResolvedValue({
      key: "empresa:37",
      id_empresa: 37,
      catalogo_version: 1,
      catalogo_synced_at: "2026-07-13T00:00:00.000Z",
      stock_snapshot_at: "2026-07-13T00:00:00.000Z",
      id_sesion_caja: 123,
    });
    jest.mocked(global.fetch).mockRejectedValue(new Error("network down"));

    await useCajaStore.getState().verificarEstadoCaja("token", {
      idEmpresa: 37,
      usarCacheDegradado: true,
    });

    expect(useCajaStore.getState().cajaAbierta).toBe(true);
    expect(useCajaStore.getState().idSesion).toBe(123);
    expect(useCajaStore.getState().modoOfflineCaja).toBe(true);
  });

  it("limpia la sesión local al cerrar caja", () => {
    useCajaStore.getState().clearCaja({
      idEmpresa: 37,
      usarCacheDegradado: true,
    });

    expect(mockedUpsertOfflineMeta).toHaveBeenCalledWith(37, {
      id_sesion_caja: null,
    });
    expect(useCajaStore.getState().cajaAbierta).toBe(false);
  });
});
