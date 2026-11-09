export const INTERVALO_REFRESCO_CATALOGO_MS_DEFAULT = 5 * 60 * 1000;

/** Milisegundos entre refrescos. Cualquier número positivo vale, así se puede bajar de 5 minutos. */
export function intervaloRefrescoCatalogoMs(
  envValue: string | undefined = process.env.NEXT_PUBLIC_CATALOGO_REFRESH_MS,
): number {
  if (envValue == null || envValue.trim() === "") {
    return INTERVALO_REFRESCO_CATALOGO_MS_DEFAULT;
  }
  const parsed = Number(envValue);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return INTERVALO_REFRESCO_CATALOGO_MS_DEFAULT;
  }
  return parsed;
}

type TimerId = ReturnType<typeof setInterval>;

export type RefrescoPeriodico = {
  tick: () => Promise<void>;
  start: () => void;
  stop: () => void;
};

export function crearRefrescoPeriodico(options: {
  intervalMs: number;
  hayConexion: () => boolean | Promise<boolean>;
  refrescar: () => Promise<unknown>;
  setIntervalFn?: (callback: () => void, intervalMs: number) => TimerId;
  clearIntervalFn?: (timer: TimerId) => void;
}): RefrescoPeriodico {
  let corriendo = false;
  let timer: TimerId | null = null;
  const setIntervalFn = options.setIntervalFn ?? setInterval;
  const clearIntervalFn = options.clearIntervalFn ?? clearInterval;

  const tick = () => {
    if (corriendo) return Promise.resolve();
    corriendo = true;

    return (async () => {
      try {
        const online = await options.hayConexion();
        if (!online) return;
        await options.refrescar();
      } catch {
        // El próximo ciclo reintenta. Una bajada fallida no toca la caché.
      } finally {
        corriendo = false;
      }
    })();
  };

  return {
    tick,
    start() {
      if (timer !== null) return;
      timer = setIntervalFn(() => {
        void tick();
      }, options.intervalMs);
    },
    stop() {
      if (timer === null) return;
      clearIntervalFn(timer);
      timer = null;
    },
  };
}
