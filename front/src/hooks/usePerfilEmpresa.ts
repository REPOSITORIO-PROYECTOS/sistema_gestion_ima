import { useEmpresaStore } from "@/lib/empresaStore";
import { PERFIL_ESTANDAR_DEFAULT, type PerfilOperativoResuelto, type TipoEsquemaEmpresa } from "@/types/perfilOperativo";

export function usePerfilEmpresa(): {
  tipoEsquema: TipoEsquemaEmpresa;
  perfil: PerfilOperativoResuelto;
} {
  const empresa = useEmpresaStore((state) => state.empresa);
  const perfil = empresa?.perfil_operativo_resuelto ?? PERFIL_ESTANDAR_DEFAULT;
  const tipoEsquema = empresa?.tipo_esquema ?? "estandar";
  return { tipoEsquema, perfil };
}
