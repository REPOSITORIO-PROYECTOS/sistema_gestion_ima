"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/authStore";

interface Empresa {
  id: number;
  nombre_legal: string;
  nombre_fantasia: string;
  cuit: string;
  activo: boolean;
}

interface Props {
  empresas: Empresa[];
  onConfigurarClick: (empresaId: number) => void;
  onActionSuccess: () => void;
}

export function EmpresasTable({ empresas, onConfigurarClick, onActionSuccess }: Props) {
  const token = useAuthStore((state) => state.token);
  const [loadingActionId, setLoadingActionId] = React.useState<number | null>(null);

  const handleToggleStatus = async (empresa: Empresa) => {
    if (!token) return;
    const accion = empresa.activo ? "desactivar" : "reactivar";
    if (confirm(`¿Seguro que quieres ${accion} la empresa "${empresa.nombre_legal}"?`)) {
      setLoadingActionId(empresa.id);
      try {
        const res = await fetch(`https://sistema-ima.sistemataup.online/api/empresas/admin/${accion}/${empresa.id}`, {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.detail || `Error al ${accion} la empresa.`);
        }
        alert(`Empresa ${accion}da con éxito.`);
        onActionSuccess();
      } catch (err) {
        if (err instanceof Error) alert(`Error: ${err.message}`);
      } finally {
        setLoadingActionId(null);
      }
    }
  };

  return (
    <div className="border rounded-md">
      <table className="w-full text-sm text-left">
        <thead className="bg-muted/50">
          <tr className="border-b">
            <th className="p-3">Nombre Legal / Fantasía</th>
            <th className="p-3">CUIT</th>
            <th className="p-3 text-center">Estado</th>
            <th className="p-3 text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {empresas.length === 0 ? (
            <tr><td colSpan={4} className="p-6 text-center text-muted-foreground">No hay empresas creadas.</td></tr>
          ) : (
            empresas.map((empresa) => (
              <tr key={empresa.id} className={`border-b last:border-0 ${!empresa.activo ? 'bg-red-50/50 text-muted-foreground' : 'hover:bg-muted/25'}`}>
                <td className="p-3">
                  <div className="font-medium">{empresa.nombre_legal}</div>
                  <div className="text-xs">{empresa.nombre_fantasia}</div>
                </td>
                <td className="p-3">{empresa.cuit}</td>
                <td className="p-3 text-center">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${empresa.activo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {empresa.activo ? 'Activa' : 'Inactiva'}
                  </span>
                </td>
                <td className="p-3 text-right space-x-2">
                  <Button variant="outline" size="sm" onClick={() => onConfigurarClick(empresa.id)}>
                    Configurar
                  </Button>
                  <Button
                    variant={empresa.activo ? "destructive" : "secondary"}
                    size="sm"
                    onClick={() => handleToggleStatus(empresa)}
                    disabled={loadingActionId === empresa.id}
                  >
                    {loadingActionId === empresa.id ? 'Cargando...' : (empresa.activo ? "Desactivar" : "Reactivar")}
                  </Button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}