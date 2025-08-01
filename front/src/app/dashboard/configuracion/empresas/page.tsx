"use client";

import * as React from "react";
import { useAuthStore } from "@/lib/authStore";
import { Button } from "@/components/ui/button";

// Importamos TODOS los componentes que necesitamos para esta página
import { EmpresasTable } from "@/components/ui/EmpresasTable";
import { CreateEmpresaModal } from "@/components/ui/CreateEmpresaModal";
import { ConfiguracionForm } from "@/components/ui/ConfiguracionForm";

// Dejamos los tipos como 'any' por ahora
interface Empresa {
  id: number;
  nombre_legal: string;
  nombre_fantasia: string;
  cuit: string;
  activo: boolean;
}

// Las props de la página ahora pueden tener un empresaId opcional
export default function PaginaGestionCompleta() {
  // Obtenemos el ID de la empresa de la URL, si existe
  const empresaIdSeleccionada = null;

  const token = useAuthStore((state) => state.token);
  const [empresas, setEmpresas] = React.useState<Empresa[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [refreshKey, setRefreshKey] = React.useState(0);

  // Función para recargar la lista de empresas
  const fetchEmpresas = React.useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/empresas/admin/lista", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("No se pudo obtener la lista de empresas.");
      const data = await res.json();
      setEmpresas(data);
    } catch (err) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Cargar datos al montar el componente o cuando se fuerza la recarga
  React.useEffect(() => {
    fetchEmpresas();
  }, [fetchEmpresas, refreshKey]);

  const handleSuccess = () => {
    setRefreshKey(oldKey => oldKey + 1); // Forzamos la recarga de la lista
  };

  // Buscamos el nombre de la empresa seleccionada para mostrarlo en el título
  const empresaSeleccionada = empresaIdSeleccionada
    ? empresas.find(e => e.id === empresaIdSeleccionada)
    : null;

  return (
    <div className="p-4 md:p-6 space-y-8">
      {/* SECCIÓN 1: CABECERA Y TABLA DE EMPRESAS */}
      <div>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold">Panel de Administración de Empresas</h1>
            <p className="text-muted-foreground">Crea, visualiza y gestiona todas las empresas clientes.</p>
          </div>
          <Button onClick={() => setIsModalOpen(true)}>Crear Nueva Empresa</Button>
        </div>

        {loading && <p>Cargando empresas...</p>}
        {error && <p className="text-red-500">Error: {error}</p>}
        
        {!loading && !error && (
          <EmpresasTable
            empresas={empresas}
            onActionSuccess={handleSuccess}
          />
        )}
      </div>

      {/* SECCIÓN 2: FORMULARIO DE CONFIGURACIÓN (SOLO SI SE HA SELECCIONADO UNA EMPRESA) */}
      {empresaIdSeleccionada && (
        <div className="border-t pt-8">
          <h2 className="text-xl font-bold">
            Configuración de: <span className="text-blue-600">{empresaSeleccionada?.nombre_legal || `Empresa ID: ${empresaIdSeleccionada}`}</span>
          </h2>
          <p className="text-muted-foreground mb-6">
            Editando la información específica para la empresa seleccionada.
          </p>
          
          {/* Aquí llamamos al componente de formulario reutilizable */}
          <ConfiguracionForm empresaId={empresaIdSeleccionada} />
        </div>
      )}

      {/* MODAL DE CREACIÓN (se renderiza pero está oculto hasta que se abre) */}
      {isModalOpen && (
        <CreateEmpresaModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSuccess={() => {
            handleSuccess();
            setIsModalOpen(false);
          }}
        />
      )}
    </div>
  );
}