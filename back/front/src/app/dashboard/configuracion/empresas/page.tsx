"use client";

import * as React from "react";
import { useAuthStore } from "@/lib/authStore";
import { Button } from "@/components/ui/button";

// Importamos los componentes hijos que construirán la interfaz
import { EmpresasTable } from "@/components/ui/EmpresasTable";
import { CreateEmpresaModal } from "@/components/ui/CreateEmpresaModal";
import { ConfiguracionForm } from "@/components/ui/ConfiguracionForm";

// Definimos la 'forma' de un objeto Empresa aquí para claridad
interface Empresa {
  id: number;
  nombre_legal: string;
  nombre_fantasia: string;
  cuit: string;
  activa: boolean;
}

// Esta es una página estática, no necesita 'params'
export default function GestionEmpresasPage() {
  const token = useAuthStore((state) => state.token);

  // --- Estados Principales ---
  const [empresas, setEmpresas] = React.useState<Empresa[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = React.useState(false);
  
  // --- Estado Clave: Guarda el ID de la empresa seleccionada para configurar ---
  const [selectedEmpresaId, setSelectedEmpresaId] = React.useState<number | null>(null);

  // --- Lógica de Obtención de Datos ---
  const fetchEmpresas = React.useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/empresas/admin/lista", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("No se pudo obtener la lista de empresas. Verifique sus permisos de administrador.");
      const data = await res.json();
      setEmpresas(data);
    } catch (err) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Se ejecuta al cargar la página
  React.useEffect(() => {
    fetchEmpresas();
  }, [fetchEmpresas]);

  // --- Funciones de Manejo de Eventos ---
  const handleActionSuccess = () => {
    fetchEmpresas(); // Recarga la lista
  };

  const empresaSeleccionada = selectedEmpresaId
    ? empresas.find(e => e.id === selectedEmpresaId)
    : null;

  return (
    <div className="p-4 md:p-6 space-y-8">
      {/* --- SECCIÓN 1: CABECERA Y TABLA --- */}
      <div>
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold">Panel de Administración de Empresas</h1>
            <p className="text-muted-foreground">Crea, visualiza y gestiona las empresas clientes.</p>
          </div>
          <Button onClick={() => setIsCreateModalOpen(true)}>Crear Nueva Empresa</Button>
        </div>

        {loading && <p className="text-center p-8">Cargando empresas...</p>}
        {error && <p className="text-red-500 bg-red-100 p-3 rounded-md">Error: {error}</p>}
        
        {!loading && !error && (
          <EmpresasTable
            empresas={empresas}
            onConfigurarClick={(empresaId) => setSelectedEmpresaId(empresaId)}
            onActionSuccess={handleActionSuccess}
          />
        )}
      </div>

      {/* --- SECCIÓN 2: FORMULARIO DE CONFIGURACIÓN --- */}
      {selectedEmpresaId && (
        <div className="border-t pt-8">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold">
              Configuración de: <span className="text-blue-600">{empresaSeleccionada?.nombre_legal || `Empresa ID: ${selectedEmpresaId}`}</span>
            </h2>
            <Button variant="ghost" onClick={() => setSelectedEmpresaId(null)}>
              Cerrar Configuración
            </Button>
          </div>
          <ConfiguracionForm empresaId={selectedEmpresaId} />
        </div>
      )}

      {/* --- MODAL DE CREACIÓN (siempre presente pero visible condicionalmente) --- */}
      <CreateEmpresaModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          handleActionSuccess();
          setIsCreateModalOpen(false);
        }}
      />
    </div>
  );
}