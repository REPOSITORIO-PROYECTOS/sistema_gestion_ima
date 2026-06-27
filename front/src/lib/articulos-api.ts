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
};

/** Catálogo completo con códigos de barras. Usar solo en pantalla de stock. */
export async function fetchAllArticulos(
  token: string,
  limit = 200,
): Promise<ArticuloCatalogoAPI[]> {
  if (!token) return [];

  let pagina = 1;
  const acumulado: ArticuloCatalogoAPI[] = [];

  while (true) {
    const respuesta = await fetch(
      `${API_CONFIG.BASE_URL}/articulos/obtener_todos?pagina=${pagina}&limite=${limit}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );

    if (!respuesta.ok) {
      throw new Error(`Fallo al obtener artículos (status ${respuesta.status})`);
    }

    const lote: ArticuloCatalogoAPI[] = await respuesta.json();
    acumulado.push(...lote);

    if (lote.length < limit) {
      break;
    }

    pagina += 1;
  }

  return acumulado;
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
