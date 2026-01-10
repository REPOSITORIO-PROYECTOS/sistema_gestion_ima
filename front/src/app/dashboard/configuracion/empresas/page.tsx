"use client";

import * as React from "react";
import { useAuthStore } from "@/lib/authStore";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

// Importamos los componentes hijos que construirán la interfaz
// Asegúrate de que estas rutas de importación sean correctas para tu proyecto
import { EmpresasTable } from "./EmpresasTable";
import { CreateEmpresaModal } from "./CreateEmpresaModal";
import { ConfiguracionForm } from "@/components/ConfiguracionForm"; // Asumo que está en la misma carpeta
import AdminGuard from "@/components/AdminGuard";

// Definimos el tipo de dato para una Empresa, que será usado en todo el componente
interface Empresa {
  id: number;
  nombre_legal: string;
  nombre_fantasia: string;
  cuit: string;
  activa: boolean;
  admin_username?: string;
  admin_user_id?: number | null;
}

export default function GestionEmpresasPage() {

  const { token } = useAuthStore();

  // --- Estados Principales ---
  const [empresas, setEmpresas] = React.useState<Empresa[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = React.useState(false);

  // --- Estado Clave: Guarda el ID de la empresa seleccionada para configurar ---
  const [selectedEmpresaId, setSelectedEmpresaId] = React.useState<number | null>(null);
  const [isConfigModalOpen, setIsConfigModalOpen] = React.useState(false);

  // --- Lógica de Obtención de Datos ---
  const fetchEmpresas = React.useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/empresas/admin/lista", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "No se pudo obtener la lista de empresas.");
      }
      const data = await res.json() as Empresa[]; // Aserción de tipo para seguridad
      setEmpresas(data);
    } catch (err) {
      if (err instanceof Error) {
        toast.error("Error al cargar empresas", { description: err.message });
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  // Se ejecuta al cargar la página y cada vez que la función fetchEmpresas se actualiza
  React.useEffect(() => {
    fetchEmpresas();
  }, [fetchEmpresas]);

  // --- Funciones de Manejo de Eventos ---
  const handleActionSuccess = () => {
    fetchEmpresas(); // Recarga la lista de empresas tras una acción exitosa
  };

  // Memoizamos el cálculo de la empresa seleccionada para optimizar el rendimiento.
  // Solo se recalculará si cambia el ID seleccionado o la lista de empresas.
  const empresaSeleccionada = React.useMemo(() =>
    selectedEmpresaId
      ? empresas.find(e => e.id === selectedEmpresaId)
      : null,
    [selectedEmpresaId, empresas]
  );

  return (
    <AdminGuard>
      <div className="p-4 md:p-6 space-y-8">
        {/* --- SECCIÓN 1: CABECERA Y TABLA --- */}
        <div>
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-2xl font-bold">Panel de Administración de Empresas</h1>
              <p className="text-muted-foreground">Crea, visualiza y gestiona las empresas clientes del sistema.</p>
            </div>
            <Button onClick={() => setIsCreateModalOpen(true)}>Crear Nueva Empresa</Button>
          </div>

          {loading && <p className="text-center p-8 text-muted-foreground">Cargando empresas...</p>}

          {!loading && (
            <EmpresasTable
              empresas={empresas}
              onConfigurarClick={(empresaId) => {
                setSelectedEmpresaId(empresaId);
                setIsConfigModalOpen(true);
              }}
              onActionSuccess={handleActionSuccess}
            />
          )}
        </div>

        <Dialog open={isConfigModalOpen} onOpenChange={(v) => {
          setIsConfigModalOpen(v);
          if (!v) setSelectedEmpresaId(null);
        }}>
          <DialogContent className="sm:max-w-2xl">
            <DialogHeader>
              <DialogTitle>Configuración de Empresa</DialogTitle>
            </DialogHeader>
            {selectedEmpresaId && (
              <div className="py-2">
                <div className="mb-4">
                  <span className="text-sm text-muted-foreground">Empresa:</span>
                  <div className="font-semibold">{empresaSeleccionada?.nombre_legal || `ID ${selectedEmpresaId}`}</div>
                </div>
                <ConfiguracionForm empresaId={selectedEmpresaId} />
              </div>
            )}
            <DialogFooter>
              <Button variant="ghost" onClick={() => {
                setIsConfigModalOpen(false);
                setSelectedEmpresaId(null);
              }}>
                Cerrar
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* --- MODAL DE CREACIÓN (CONTROLADO POR ESTADO) --- */}
        <CreateEmpresaModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          onSuccess={() => {
            handleActionSuccess();
            setIsCreateModalOpen(false); // Cierra el modal tras el éxito
          }}
        />
      </div>
    </AdminGuard>
  );
}
