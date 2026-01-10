"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/authStore";

interface Empresa {
  id: number;
  nombre_legal: string;
  nombre_fantasia: string;
  cuit: string;
  activa: boolean;
  admin_username?: string;
  admin_user_id?: number | null;
}

interface Props {
  empresas: Empresa[];
  onConfigurarClick: (empresaId: number) => void;
  onActionSuccess: () => void;
}

export function EmpresasTable({ empresas, onConfigurarClick, onActionSuccess }: Props) {
  const token = useAuthStore((state) => state.token);
  const [loadingActionId, setLoadingActionId] = React.useState<number | null>(null);
  const [changingId, setChangingId] = React.useState<number | null>(null);

  const handleToggleStatus = async (empresa: Empresa) => {
    if (!token) return;
    const accion = empresa.activa ? "desactivar" : "reactivar";
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

  const handleChangeAdminPassword = async (empresa: Empresa) => {
    if (!token) return;
    if (!empresa.admin_user_id) {
      alert("No se encontró el usuario administrador asociado a esta empresa.");
      return;
    }
    const nueva = prompt(`Ingrese la nueva contraseña para el admin de "${empresa.nombre_legal}":`);
    if (!nueva || nueva.length < 8) {
      alert("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    setChangingId(empresa.id);
    try {
      const res = await fetch(`https://sistema-ima.sistemataup.online/api/admin/usuarios/${empresa.admin_user_id}/password`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ nueva_password: nueva })
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error al actualizar la contraseña.");
      }
      alert("Contraseña actualizada correctamente.");
      onActionSuccess();
    } catch (err) {
      if (err instanceof Error) alert(`Error: ${err.message}`);
    } finally {
      setChangingId(null);
    }
  };

  return (
    <div className="border rounded-md">
      <table className="w-full text-sm text-left">
        <thead className="bg-muted/50">
          <tr className="border-b">
            <th className="p-3">Nombre Legal / Fantasía</th>
            <th className="p-3">CUIT</th>
            <th className="p-3">Admin</th>
            <th className="p-3 text-center">Estado</th>
            <th className="p-3 text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {empresas.length === 0 ? (
            <tr><td colSpan={4} className="p-6 text-center text-muted-foreground">No hay empresas creadas.</td></tr>
          ) : (
            empresas.map((empresa) => (
              <tr key={empresa.id} className={`border-b last:border-0 ${!empresa.activa ? 'bg-red-50/50 text-muted-foreground' : 'hover:bg-muted/25'}`}>
                <td className="p-3">
                  <div className="font-medium">{empresa.nombre_legal}</div>
                  <div className="text-xs">{empresa.nombre_fantasia}</div>
                </td>
                <td className="p-3">{empresa.cuit}</td>
                <td className="p-3">{empresa.admin_username || "N/A"}</td>
                <td className="p-3 text-center">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${empresa.activa ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {empresa.activa ? 'Activa' : 'Inactiva'}
                  </span>
                </td>
                <td className="p-3 text-right space-x-2">
                  <Button variant="outline" size="sm" onClick={() => onConfigurarClick(empresa.id)}>
                    Configurar
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleChangeAdminPassword(empresa)}
                    disabled={changingId === empresa.id}
                  >
                    {changingId === empresa.id ? 'Actualizando...' : 'Cambiar contraseña'}
                  </Button>
                  <Button
                    variant={empresa.activa ? "destructive" : "secondary"}
                    size="sm"
                    onClick={() => handleToggleStatus(empresa)}
                    disabled={loadingActionId === empresa.id}
                  >
                    {loadingActionId === empresa.id ? 'Cargando...' : (empresa.activa ? "Desactivar" : "Reactivar")}
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
