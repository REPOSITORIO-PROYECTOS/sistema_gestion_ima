import { actualizarTodasLasLineas, type LineaCaja } from "@/lib/actualizar-precios-caja";
import type { ArticuloCatalogoAPI } from "@/lib/articulos-api";
import { refreshCatalogoCache, type RefreshCatalogoOptions } from "@/lib/offline/catalogo-cache";

export type ResultadoActualizacion =
  | {
      ok: true;
      lineas: LineaCaja[];
      actualizadas: number;
      total: number;
      articulos: ArticuloCatalogoAPI[];
    }
  | { ok: false; motivo: "sin_conexion" | "error" };

export async function ejecutarActualizacionPrecios(params: {
  token: string;
  idEmpresa: number;
  hayConexion: () => boolean | Promise<boolean>;
  lineas: LineaCaja[];
  tipoClienteId: string;
  opcionesDescarga?: RefreshCatalogoOptions;
}): Promise<ResultadoActualizacion> {
  const online = await params.hayConexion();
  if (!online) {
    return { ok: false, motivo: "sin_conexion" };
  }

  try {
    const descargado = await refreshCatalogoCache(params.token, params.idEmpresa, {
      ...params.opcionesDescarga,
      force: true,
    });
    if (!descargado.articulos) {
      return { ok: false, motivo: "error" };
    }

    const precios = new Map(
      descargado.articulos.map((articulo) => [
        String(articulo.id),
        {
          precio_venta: articulo.precio_venta,
          venta_negocio: articulo.venta_negocio,
          precio_manual: articulo.precio_manual ?? false,
        },
      ]),
    );
    const aplicado = actualizarTodasLasLineas(params.lineas, precios, params.tipoClienteId);

    return {
      ok: true,
      lineas: aplicado.lineas,
      actualizadas: aplicado.actualizadas,
      total: descargado.articulos_count,
      articulos: descargado.articulos,
    };
  } catch (error) {
    console.error("Actualización de precios fallida:", error);
    return { ok: false, motivo: "error" };
  }
}

export function mensajeToastActualizacion(
  resultado: ResultadoActualizacion,
): { tipo: "success" | "error"; texto: string } {
  if (!resultado.ok) {
    if (resultado.motivo === "sin_conexion") {
      return { tipo: "error", texto: "Sin conexión no pude actualizar los precios." };
    }
    return {
      tipo: "error",
      texto: "No pude actualizar los precios. El caché anterior sigue vigente.",
    };
  }

  if (resultado.actualizadas > 0) {
    return {
      tipo: "success",
      texto: `Actualicé ${resultado.total} precios del catálogo y ${resultado.actualizadas} del resumen.`,
    };
  }

  return {
    tipo: "success",
    texto: `Actualicé ${resultado.total} precios del catálogo.`,
  };
}
