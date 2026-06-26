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
import { AfipToolsPanel } from "@/components/AfipToolsPanel";

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
  const [configSavedAt, setConfigSavedAt] = React.useState<string | null>(null);
  const [afipToolsStatus, setAfipToolsStatus] = React.useState<string | null>(null);

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

  React.useEffect(() => {
    setConfigSavedAt(null);
    setAfipToolsStatus(null);
  }, [selectedEmpresaId]);

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
          <DialogContent className="flex max-h-[92vh] w-[calc(100%-1.5rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-3xl">
            <DialogHeader className="shrink-0 border-b px-6 py-4 pr-12">
              <DialogTitle>Configuración de Empresa</DialogTitle>
            </DialogHeader>

            {selectedEmpresaId && (
              <>
                <div className="shrink-0 space-y-4 border-b bg-slate-50/80 px-6 py-4">
                  <div className="space-y-1">
                    <span className="text-sm text-muted-foreground">Empresa</span>
                    <div className="text-xl font-semibold text-slate-900 sm:text-2xl">
                      {empresaSeleccionada?.nombre_legal || `ID ${selectedEmpresaId}`}
                    </div>
                    <p className="text-sm text-slate-600">
                      Datos fiscales, modo especial y certificados AFIP.
                    </p>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                      <p className="text-xs uppercase tracking-wider text-slate-500">CUIT</p>
                      <p className="text-base font-semibold text-slate-900">{empresaSeleccionada?.cuit || "-"}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                      <p className="text-xs uppercase tracking-wider text-slate-500">Estado</p>
                      <p className={`text-sm font-semibold ${empresaSeleccionada?.activa ? "text-emerald-700" : "text-rose-600"}`}>
                        {empresaSeleccionada?.activa ? "Activa" : "Inactiva"}
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                      <p className="text-xs uppercase tracking-wider text-slate-500">Admin</p>
                      <p className="text-sm font-semibold text-slate-900">{empresaSeleccionada?.admin_username || "Sin admin"}</p>
                    </div>
                  </div>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-4">
                  <div className="space-y-6 pb-2">
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
                      <div className="mb-4 flex items-center justify-between gap-2">
                        <h3 className="text-lg font-semibold text-slate-900">Configuración General & AFIP</h3>
                        <span className={`shrink-0 text-xs font-semibold ${configSavedAt ? "text-emerald-600" : "text-slate-500"}`}>
                          {configSavedAt ? `Guardado ${configSavedAt}` : "Sin guardar"}
                        </span>
                      </div>
                      <ConfiguracionForm
                        empresaId={selectedEmpresaId}
                        sections={{ general: true, afip: true, balanza: false, modoEspecial: true }}
                        onSave={() => setConfigSavedAt(new Date().toLocaleTimeString())}
                      />
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
                      <div className="mb-4 flex items-center justify-between gap-2">
                        <h3 className="text-lg font-semibold text-slate-900">Herramientas AFIP</h3>
                        <span className={`shrink-0 text-xs font-semibold ${afipToolsStatus ? "text-emerald-600" : "text-slate-500"}`}>
                          {afipToolsStatus || "Sin acciones"}
                        </span>
                      </div>
                      <AfipToolsPanel
                        empresaId={selectedEmpresaId}
                        onSuccess={(message) => setAfipToolsStatus(`${message} ${new Date().toLocaleTimeString()}`)}
                      />
                    </div>
                  </div>
                </div>

                <DialogFooter className="shrink-0 border-t bg-background px-6 py-4">
                  <Button variant="ghost" onClick={() => {
                    setIsConfigModalOpen(false);
                    setSelectedEmpresaId(null);
                  }}>
                    Cerrar
                  </Button>
                </DialogFooter>
              </>
            )}
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
