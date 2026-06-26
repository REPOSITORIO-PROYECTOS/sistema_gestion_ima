import { API_CONFIG } from "@/lib/api-config";

export type UnidadMedida =
  | "unidad"
  | "gramos"
  | "kilogramos"
  | "litros"
  | "mililitros";

export interface ProductoModoEspecial {
  id: number;
  codigo_interno: string;
  descripcion: string;
  precio_venta: number;
  precio_costo: number;
  venta_negocio: number;
  categorias: string[];
  stock_actual: number;
  stock_minimo?: number | null;
  barcodes: string[];
  unidad: string;
  cantidad_envase?: number | null;
  ubicacion?: string | null;
  activo: boolean;
}

export interface ProductoFormData {
  codigo_interno: string;
  descripcion: string;
  precio_venta: string;
  precio_costo: string;
  categorias: string;
  stock: string;
  stock_minimo: string;
  barcodes: string;
  unidad: UnidadMedida;
  cantidad_envase: string;
  ubicacion: string;
}

const headers = (token: string) => ({
  Authorization: `Bearer ${token}`,
  "Content-Type": "application/json",
});

function parsePayload(form: ProductoFormData) {
  const categorias = form.categorias
    .split(/[,;|]/)
    .map((c) => c.trim())
    .filter(Boolean);
  const barcodes = form.barcodes
    .split(/[,;|]/)
    .map((c) => c.trim())
    .filter(Boolean);

  return {
    codigo_interno: form.codigo_interno.trim(),
    descripcion: form.descripcion.trim(),
    precio_venta: parseFloat(form.precio_venta),
    precio_costo: form.precio_costo ? parseFloat(form.precio_costo) : undefined,
    categorias,
    stock: form.stock ? parseFloat(form.stock) : undefined,
    stock_minimo: form.stock_minimo ? parseFloat(form.stock_minimo) : undefined,
    barcodes: barcodes.length > 0 ? barcodes : undefined,
    unidad: form.unidad,
    cantidad_envase: form.cantidad_envase ? parseFloat(form.cantidad_envase) : undefined,
    ubicacion: form.ubicacion.trim() || undefined,
  };
}

export async function fetchProductosModoEspecial(token: string): Promise<ProductoModoEspecial[]> {
  const res = await fetch(`${API_CONFIG.BASE_URL}/modo-especial/productos`, {
    headers: headers(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "No se pudieron cargar los productos.");
  }
  return res.json();
}

export async function crearProductoModoEspecial(token: string, form: ProductoFormData) {
  const res = await fetch(`${API_CONFIG.BASE_URL}/modo-especial/productos`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify(parsePayload(form)),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Error al crear el producto.");
  }
  return res.json();
}

export async function actualizarProductoModoEspecial(
  token: string,
  codigoInterno: string,
  form: Partial<ProductoFormData>,
) {
  const payload: Record<string, unknown> = {};
  if (form.descripcion) payload.descripcion = form.descripcion.trim();
  if (form.precio_venta) payload.precio_venta = parseFloat(form.precio_venta);
  if (form.precio_costo) payload.precio_costo = parseFloat(form.precio_costo);
  if (form.categorias) {
    payload.categorias = form.categorias.split(/[,;|]/).map((c) => c.trim()).filter(Boolean);
  }
  if (form.stock) payload.stock = parseFloat(form.stock);
  if (form.stock_minimo) payload.stock_minimo = parseFloat(form.stock_minimo);
  if (form.barcodes !== undefined) {
    const barcodes = form.barcodes.split(/[,;|]/).map((c) => c.trim()).filter(Boolean);
    payload.barcodes = barcodes;
  }
  if (form.unidad) payload.unidad = form.unidad;
  if (form.cantidad_envase) payload.cantidad_envase = parseFloat(form.cantidad_envase);
  if (form.ubicacion !== undefined) payload.ubicacion = form.ubicacion.trim() || null;

  const res = await fetch(`${API_CONFIG.BASE_URL}/modo-especial/productos/${encodeURIComponent(codigoInterno)}`, {
    method: "PUT",
    headers: headers(token),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Error al actualizar el producto.");
  }
  return res.json();
}

export async function ingresarStockModoEspecial(
  token: string,
  items: { codigo_interno: string; cantidad: number; observacion?: string }[],
) {
  const res = await fetch(`${API_CONFIG.BASE_URL}/modo-especial/ingreso-stock`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify({ items }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Error al registrar ingreso de stock.");
  }
  return res.json();
}

export async function subaPreciosModoEspecial(
  token: string,
  data: { porcentaje_general?: number; categoria?: string },
) {
  const res = await fetch(`${API_CONFIG.BASE_URL}/modo-especial/suba-precios`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Error en la suba de precios.");
  }
  return res.json();
}

export async function exportarProductosModoEspecial(token: string): Promise<Blob> {
  const res = await fetch(`${API_CONFIG.BASE_URL}/modo-especial/exportar`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Error al exportar productos.");
  }
  return res.blob();
}

export async function importarProductosModoEspecial(token: string, file: File) {
  const formData = new FormData();
  formData.append("archivo", file);
  const res = await fetch(`${API_CONFIG.BASE_URL}/modo-especial/importar`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Error al importar productos.");
  }
  return res.json();
}
