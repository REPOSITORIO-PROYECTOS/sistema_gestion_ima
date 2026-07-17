import type { PerfilOperativoResuelto, TipoEsquemaEmpresa } from "@/types/perfilOperativo";

const PLANTILLAS_CON_CACHE_DEGRADADO = new Set(["modo_especial_demo", "modo_especial_pos"]);

/** Resuelve flag aunque el backend no lo serialice (perfiles migrados antes del campo). */
export function resolveCacheDegradado(
  perfil: Pick<PerfilOperativoResuelto, "cache_degradado" | "plantilla_origen">,
): boolean {
  if (perfil.cache_degradado === true) return true;
  if (perfil.cache_degradado === false) return false;
  const origen = perfil.plantilla_origen;
  return Boolean(origen && PLANTILLAS_CON_CACHE_DEGRADADO.has(origen));
}

/** Offline degradado solo en empresas especiales con flag explícito (D1). */
export function isCacheDegradadoActivo(
  tipoEsquema: TipoEsquemaEmpresa,
  perfil: Pick<PerfilOperativoResuelto, "cache_degradado" | "plantilla_origen">,
): boolean {
  return tipoEsquema === "especial" && resolveCacheDegradado(perfil);
}
