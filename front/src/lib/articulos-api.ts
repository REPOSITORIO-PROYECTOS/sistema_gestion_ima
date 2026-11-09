import { API_CONFIG } from "./api-config";

export type ArticuloCatalogoAPI = {
  id: number | string;
  nombre?: string;
  descripcion?: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
  unidad_venta: string;
  precio_manual?: boolean;
  activo?: boolean;
  codigo_interno?: string | null;
  codigos?: { codigo: string }[];
};

export const TIMEOUT_PAGINA_CATALOGO_MS = 20_000;
const TOPE_PAGINAS_CATALOGO = 500;

export type CatalogoMeta = {
  version: number;
  total: number;
};

export type CatalogoDescarga = {
  articulos: ArticuloCatalogoAPI[];
  version: number;
  total: number;
};

export type FetchCatalogoOptions = {
  limit?: number;
  timeoutMs?: number;
  orden?: "id" | "descripcion";
};

function esAbort(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

async function fetchConTimeout(
  url: string,
  token: string,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: controller.signal,
    });
  } catch (error) {
    if (esAbort(error)) {
      throw new Error(`Tiempo agotado al pedir el catálogo (${timeoutMs} ms).`);
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchCatalogoVersion(token: string): Promise<number> {
  if (!token) return 0;
  const meta = await fetchCatalogoMeta(token);
  return meta.version;
}

export async function fetchCatalogoMeta(
  token: string,
  timeoutMs = TIMEOUT_PAGINA_CATALOGO_MS,
): Promise<CatalogoMeta> {
  if (!token) {
    throw new Error("No hay sesión para leer el catálogo.");
  }

  const respuesta = await fetchConTimeout(
    `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.ARTICULOS_VERSION}`,
    token,
    timeoutMs,
  );

  if (!respuesta.ok) {
    throw new Error(`Fallo al obtener versión de catálogo (status ${respuesta.status})`);
  }

  const data = (await respuesta.json()) as { version?: number; total?: number };
  if (typeof data.total !== "number" || !Number.isFinite(data.total) || data.total < 0) {
    throw new Error("El servidor no confirmó el total del catálogo.");
  }

  return { version: data.version ?? 0, total: data.total };
}

/**
 * Baja el catálogo activo completo, paginado por id.
 * Si una página falla, vence el tiempo o el total no cierra, lanza error
 * y no devuelve una lista parcial.
 */
export async function fetchCatalogoCompleto(
  token: string,
  options: FetchCatalogoOptions = {},
): Promise<CatalogoDescarga> {
  if (!token) {
    throw new Error("No hay sesión para leer el catálogo.");
  }

  const limit = options.limit ?? 200;
  const timeoutMs = options.timeoutMs ?? TIMEOUT_PAGINA_CATALOGO_MS;
  const orden = options.orden ?? "id";
  const meta = await fetchCatalogoMeta(token, timeoutMs);
  const acumulado: ArticuloCatalogoAPI[] = [];
  const ids = new Set<string>();
  let pagina = 1;

  while (acumulado.length < meta.total) {
    if (pagina > TOPE_PAGINAS_CATALOGO) {
      throw new Error("El catálogo superó el tope de páginas.");
    }

    const respuesta = await fetchConTimeout(
      `${API_CONFIG.BASE_URL}/articulos/obtener_todos?pagina=${pagina}&limite=${limit}&orden=${orden}`,
      token,
      timeoutMs,
    );

    if (!respuesta.ok) {
      throw new Error(`Fallo al obtener artículos (status ${respuesta.status})`);
    }

    const lote = (await respuesta.json()) as ArticuloCatalogoAPI[];
    if (!Array.isArray(lote)) {
      throw new Error("Respuesta de catálogo inválida.");
    }
    if (lote.length === 0) {
      throw new Error(
        `Catálogo incompleto: llegaron ${acumulado.length} de ${meta.total}.`,
      );
    }

    for (const articulo of lote) {
      const id = String(articulo.id);
      if (ids.has(id)) {
        throw new Error("Paginación de catálogo inestable: id repetido.");
      }
      ids.add(id);
      acumulado.push(articulo);
    }

    if (acumulado.length > meta.total) {
      throw new Error(
        `Catálogo inconsistente: llegaron ${acumulado.length} y el total es ${meta.total}.`,
      );
    }

    pagina += 1;
  }

  if (acumulado.length !== meta.total) {
    throw new Error(
      `Catálogo incompleto: llegaron ${acumulado.length} de ${meta.total}.`,
    );
  }

  return { articulos: acumulado, version: meta.version, total: meta.total };
}

/** Catálogo completo. Atajo de fetchCatalogoCompleto, sin lista parcial. */
export async function fetchAllArticulos(
  token: string,
  limit = 200,
): Promise<ArticuloCatalogoAPI[]> {
  if (!token) return [];
  const descarga = await fetchCatalogoCompleto(token, { limit, orden: "id" });
  return descarga.articulos;
}

export function mapArticulosToStore(data: ArticuloCatalogoAPI[]) {
  return data.map((p) => ({
    id: String(p.id),
    nombre: p.nombre ?? p.descripcion ?? "",
    precio_venta: p.precio_venta,
    venta_negocio: p.venta_negocio,
    stock_actual: p.stock_actual,
    unidad_venta: p.unidad_venta || "Unidad",
    precio_manual: p.precio_manual ?? false,
  }));
}

export async function fetchArticuloPorId(
  token: string,
  id: number | string,
): Promise<ArticuloCatalogoAPI | null> {
  if (!token || !id) return null;

  const respuesta = await fetch(`${API_CONFIG.BASE_URL}/articulos/obtener/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!respuesta.ok) return null;
  return respuesta.json();
}
