"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import PanelEstadisticasCaja from "@/components/PanelEstadisticasCaja";
import { useEmpresaStore } from "@/lib/empresaStore";
import { empresaTienePanelEstadisticas } from "@/lib/permisos";

export default function EstadisticasPage() {
  const empresa = useEmpresaStore((state) => state.empresa);

  if (!empresaTienePanelEstadisticas(empresa?.id_empresa)) {
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
