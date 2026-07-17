import {
  getOfflineStatusLabel,
  isBrowserOnline,
  pingServidor,
} from "@/lib/offline/connectivity";

describe("connectivity", () => {
  beforeEach(() => {
    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      value: true,
    });
    global.fetch = jest.fn().mockResolvedValue({});
  });

  it("mapea labels operativos", () => {
    expect(getOfflineStatusLabel("online")).toBe("Conectado");
    expect(getOfflineStatusLabel("browser_offline")).toBe("Sin conexión");
    expect(getOfflineStatusLabel("server_unreachable")).toBe("Sin servidor");
  });

  it("detecta navegador offline", async () => {
    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      value: false,
    });

    expect(isBrowserOnline()).toBe(false);
    await expect(pingServidor("token")).resolves.toBe(false);
  });

  it("considera alcanzable al servidor si responde HTTP", async () => {
    await expect(pingServidor("token")).resolves.toBe(true);
  });
});
