"use client";

import { useEmpresaStore } from "@/lib/empresaStore";
import { useAuthStore } from "@/lib/authStore";
import { puedeVerPanelEstadisticas, empresaTienePanelEstadisticas } from "@/lib/permisos";
import { usePerfilEmpresa } from "@/hooks/usePerfilEmpresa";
import PanelEstadisticasCaja from "@/components/PanelEstadisticasCaja";

export default function Inicio() {
  const empresa = useEmpresaStore((state) => state.empresa);
  const role = useAuthStore((state) => state.role);
  const { perfil } = usePerfilEmpresa();

  const mostrarPanel =
    empresaTienePanelEstadisticas(perfil) &&
    puedeVerPanelEstadisticas(role?.nombre);

  return (
    <div className="flex flex-col items-center gap-8 w-full max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold text-green-950 text-center">
        {`Sistema de Gestión - ${empresa?.nombre_negocio ?? ""}`}
      </h1>

      {mostrarPanel && (
        <div className="w-full">
          <PanelEstadisticasCaja compact />
        </div>
      )}
    </div>
  );
}
