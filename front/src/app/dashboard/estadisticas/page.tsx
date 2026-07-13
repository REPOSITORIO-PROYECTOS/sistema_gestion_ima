"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import PanelEstadisticasCaja from "@/components/PanelEstadisticasCaja";
import { empresaTienePanelEstadisticas } from "@/lib/permisos";
import { usePerfilEmpresa } from "@/hooks/usePerfilEmpresa";

export default function EstadisticasPage() {
  const { perfil } = usePerfilEmpresa();

  if (!empresaTienePanelEstadisticas(perfil)) {
    return (
      <ProtectedRoute allowedRoles={["Admin", "Gerente", "Encargada", "Soporte"]}>
        <div className="text-center py-12 text-gray-600">
          El panel de estadísticas no está habilitado para esta empresa.
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute allowedRoles={["Admin", "Gerente", "Encargada", "Soporte"]}>
      <PanelEstadisticasCaja />
    </ProtectedRoute>
  );
}
