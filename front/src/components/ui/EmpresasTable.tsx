"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/authStore";
import Link from "next/link"; // Importante para la navegación

// Por tu solicitud, evitamos crear un archivo de tipos separado.
// Definimos la forma de 'Empresa' aquí mismo para claridad.
interface Empresa {
  id: number;
  nombre_legal: string;
  nombre_fantasia: string;
  cuit: string;
  activo: boolean;
}

interface Props {
  empresas: Empresa[];
  onActionSuccess: () => void; // Función para recargar la lista desde la página principal
}

export function EmpresasTable({ empresas, onActionSuccess }: Props) {
  const token = useAuthStore((state) => state.token);
  // Estado para mostrar 'Cargando...' solo en el botón presionado
  const [loadingActionId, setLoadingActionId] = React.useState<number | null>(null);

  const handleToggleStatus = async (empresa: Empresa) => {
    if (!token) {
      alert("Error de autenticación. Por favor, inicie sesión de nuevo.");
      return;
    }

    const accion = empresa.activo ? "desactivar" : "reactivar";
    const confirmMessage = `¿Estás seguro de que quieres ${accion} la empresa "${empresa.nombre_legal}"?`;
    
    if (window.confirm(confirmMessage)) {
      setLoadingActionId(empresa.id); // Activa el estado de carga para este botón
      
      const url = `https://sistema-ima.sistemataup.online/api/empresas/admin/${accion}/${empresa.id}`;
      
      try {
        const res = await fetch(url, {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.detail || `Error del servidor al ${accion} la empresa.`);
        }
        
        alert(`Empresa ${accion === 'desactivar' ? 'desactivada' : 'reactivada'} con éxito.`);
        onActionSuccess(); // Llama a la función para recargar la tabla

      } catch (err) {
        if (err instanceof Error) {
          alert(`Error: ${err.message}`);
        }
      } finally {
        setLoadingActionId(null); // Desactiva el estado de carga, incluso si hay un error
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
            <tr>
              <td colSpan={4} className="p-6 text-center text-muted-foreground">
                No se encontraron empresas. ¡Crea la primera!
              </td>
            </tr>
          ) : (
            empresas.map((empresa) => (
              <tr 
                key={empresa.id} 
                className={`border-b last:border-0 ${!empresa.activo ? 'bg-red-50/50 text-muted-foreground' : 'hover:bg-muted/25'}`}
              >
                <td className="p-3">
                  <div className="font-medium">{empresa.nombre_legal}</div>
                  <div className="text-xs text-muted-foreground">{empresa.nombre_fantasia}</div>
                </td>
                <td className="p-3">{empresa.cuit}</td>
                <td className="p-3 text-center">
                  <span 
                    className={`px-2 py-1 text-xs font-semibold rounded-full ${empresa.activo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}
                  >
                    {empresa.activo ? 'Activa' : 'Inactiva'}
                  </span>
                </td>
                <td className="p-3 text-right space-x-2">
                  <Button asChild variant="outline" size="sm">
                    <Link href={`/dashboard/admin/empresas/${empresa.id}/configuracion`}>
                      Configurar
                    </Link>
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