import {
  INTERVALO_REFRESCO_CATALOGO_MS_DEFAULT,
  crearRefrescoPeriodico,
  intervaloRefrescoCatalogoMs,
} from "../catalogo-refresh-scheduler";

describe("intervalo de refresco del catálogo", () => {
  it("por defecto espera 5 minutos y acepta bajarlo", () => {
    expect(intervaloRefrescoCatalogoMs(undefined)).toBe(INTERVALO_REFRESCO_CATALOGO_MS_DEFAULT);
    expect(intervaloRefrescoCatalogoMs("")).toBe(5 * 60 * 1000);
    expect(intervaloRefrescoCatalogoMs("15000")).toBe(15_000);
    expect(intervaloRefrescoCatalogoMs("0")).toBe(INTERVALO_REFRESCO_CATALOGO_MS_DEFAULT);
  });
});

describe("refresco periódico", () => {
  afterEach(() => {
    jest.useRealTimers();
  });

  it("con conexión refresca y sin conexión no pide nada", async () => {
    const refrescar = jest.fn().mockResolvedValue(undefined);
    const sinRed = crearRefrescoPeriodico({
      intervalMs: 1000,
      hayConexion: () => false,
      refrescar,
    });
    await sinRed.tick();
    expect(refrescar).not.toHaveBeenCalled();

    const conRed = crearRefrescoPeriodico({
      intervalMs: 1000,
      hayConexion: () => true,
      refrescar,
    });
    await conRed.tick();
    expect(refrescar).toHaveBeenCalledTimes(1);
  });

  it("no lanza otro refresco mientras hay uno en curso", async () => {
    let soltar: () => void = () => undefined;
    const refrescar = jest.fn(
      () =>
        new Promise<void>((resolve) => {
          soltar = resolve;
        }),
    );
    const scheduler = crearRefrescoPeriodico({
      intervalMs: 1000,
      hayConexion: () => true,
      refrescar,
    });

    const primero = scheduler.tick();
    const segundo = scheduler.tick();
    await Promise.resolve();
    expect(refrescar).toHaveBeenCalledTimes(1);

    soltar();
    await primero;
    await segundo;
    expect(refrescar).toHaveBeenCalledTimes(1);
  });

  it("el intervalo dispara con conexión y se detiene al parar", async () => {
    jest.useFakeTimers();
    const refrescar = jest.fn().mockResolvedValue(undefined);
    const scheduler = crearRefrescoPeriodico({
      intervalMs: 5_000,
      hayConexion: () => true,
      refrescar,
    });

    scheduler.start();
    expect(refrescar).not.toHaveBeenCalled();

    await jest.advanceTimersByTimeAsync(5_000);
    expect(refrescar).toHaveBeenCalledTimes(1);

    await jest.advanceTimersByTimeAsync(5_000);
    expect(refrescar).toHaveBeenCalledTimes(2);

    scheduler.stop();
    await jest.advanceTimersByTimeAsync(10_000);
    expect(refrescar).toHaveBeenCalledTimes(2);
    jest.useRealTimers();
  });

  it("al volver la red reintenta solo si hay conexión", async () => {
    const refrescar = jest.fn().mockResolvedValue(undefined);
    let online = false;
    const scheduler = crearRefrescoPeriodico({
      intervalMs: 60_000,
      hayConexion: () => online,
      refrescar,
    });

    await scheduler.tick();
    expect(refrescar).not.toHaveBeenCalled();

    online = true;
    await scheduler.tick();
    expect(refrescar).toHaveBeenCalledTimes(1);
  });
});
