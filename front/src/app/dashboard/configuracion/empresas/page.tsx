"use client";

import { useState, useEffect, FormEvent, ChangeEvent, Fragment } from "react";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, Settings, FileKey, UploadCloud } from "lucide-react";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription, 
  DialogFooter,
  DialogClose
} from "@/components/ui/dialog";

// --- Interfaces y Tipos ---
interface Empresa {
  id: number;
  nombre_legal: string;
  nombre_fantasia?: string;
  cuit: string;
  activa: boolean;
}

const API_URL = "https://sistema-ima.sistemataup.online/api";

// --- Componente del Asistente AFIP ---
function AfipWizard({ empresa }: { empresa: Empresa }) {
  // ... (El código del AfipWizard no tiene errores, puede permanecer igual)
  const token = useAuthStore((state) => state.token);
  const [isLoading, setIsLoading] = useState(false);
  const [csrGenerado, setCsrGenerado] = useState(false);
  const [certificadoFile, setCertificadoFile] = useState<File | null>(null);

  const downloadFile = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleGenerarCSR = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/afip-tools/generar-csr`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ cuit: empresa.cuit, razon_social: empresa.nombre_legal }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error al generar el CSR.");
      }
      const blob = await res.blob();
      downloadFile(blob, `${empresa.cuit}.csr`);
      toast.success("Archivo .csr descargado. Siga las instrucciones del Paso 2.");
      setCsrGenerado(true);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Error inesperado.");
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setCertificadoFile(e.target.files[0]);
  };

  const handleSubirCertificado = async () => {
    if (!certificadoFile) return toast.error("Por favor, seleccione el archivo .crt.");
    
    const lector = new FileReader();
    lector.readAsText(certificadoFile);
    lector.onload = async () => {
      const certificadoPem = lector.result as string;
      setIsLoading(true);
      try {
        const res = await fetch(`${API_URL}/afip-tools/subir-certificado`, {
          method: 'POST',
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ cuit: empresa.cuit, certificado_pem: certificadoPem }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        toast.success("¡Credenciales guardadas en la bóveda de forma segura!");
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Error inesperado.");
      } finally {
        setIsLoading(false);
      }
    };
    lector.onerror = () => toast.error("No se pudo leer el archivo.");
  };

  return (
    <div className="p-4 border rounded-lg mt-4 bg-gray-50">
      <h3 className="font-semibold text-lg flex items-center gap-2"><FileKey size={20}/> Credenciales de Facturación AFIP</h3>
      <div className="mt-4 space-y-6">
        <div>
          <h4 className="font-semibold">Paso 1: Generar Solicitud de Certificado (.csr)</h4>
          <p className="text-sm text-gray-600">
            Esto creará una clave privada segura en el servidor y le permitirá descargar la solicitud.
          </p>
          <Button onClick={handleGenerarCSR} disabled={isLoading} className="mt-2">
            <Loader2 className={`animate-spin mr-2 h-4 w-4 ${!isLoading && 'hidden'}`} />
            Generar y Descargar .csr
          </Button>
        </div>
        
        {csrGenerado && (
          <Fragment>
            <div className="border-t pt-4">
              <h4 className="font-semibold">Paso 2: Obtener Certificado en el sitio de AFIP</h4>
              <p className="text-sm text-gray-600">
                Vaya a Administración de Certificados Digitales en el portal de AFIP, añada un alias para su sistema y suba el archivo <code>{empresa.cuit}.csr</code> que acaba de descargar.
              </p>
            </div>
            <div className="border-t pt-4">
              <h4 className="font-semibold">Paso 3: Subir Certificado (.crt) y Guardar en Bóveda</h4>
              <p className="text-sm text-gray-600">
                Seleccione el archivo <code>.crt</code> que obtuvo de AFIP para guardarlo de forma segura.
              </p>
              <div className="flex items-center gap-2 mt-2">
                <Input type="file" accept=".crt" onChange={handleFileChange} />
                <Button onClick={handleSubirCertificado} disabled={isLoading || !certificadoFile}>
                  <UploadCloud className={`mr-2 h-4 w-4 ${isLoading && 'hidden'}`} />
                  <Loader2 className={`animate-spin mr-2 h-4 w-4 ${!isLoading && 'hidden'}`} />
                  Guardar
                </Button>
              </div>
            </div>
          </Fragment>
        )}
      </div>
    </div>
  );
}

// --- COMPONENTE PRINCIPAL DE LA PÁGINA ---
export default function ConfiguracionEmpresasPage() {
  const token = useAuthStore((state) => state.token);
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [nombreLegal, setNombreLegal] = useState("");
  const [nombreFantasia, setNombreFantasia] = useState("");
  const [cuit, setCuit] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [empresaSeleccionada, setEmpresaSeleccionada] = useState<Empresa | null>(null);

  // --- CORRECCIÓN DEL useEffect ---
  useEffect(() => {
    // Definimos la función DENTRO del useEffect para resolver la advertencia de dependencias.
    const fetchEmpresas = async () => {
      if (!token) return;
      setIsLoadingList(true);
      try {
        const res = await fetch(`${API_URL}/empresas/admin/lista`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          throw new Error("No se pudo cargar la lista de empresas.");
        }
        setEmpresas(await res.json());
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Error al cargar empresas.");
      } finally {
        setIsLoadingList(false);
      }
    };

    fetchEmpresas();
  }, [token]); // El array de dependencias ahora es correcto.

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!nombreLegal || !cuit) return toast.error("Nombre Legal y CUIT son obligatorios.");
    if (cuit.length !== 11) return toast.error("El CUIT debe tener 11 dígitos.");
    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/empresas/admin/crear`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ nombre_legal: nombreLegal, nombre_fantasia: nombreFantasia || null, cuit }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "No se pudo crear la empresa.");
      toast.success("¡Empresa creada exitosamente!");
      // Refrescamos la lista llamando a la función que la obtiene
      // Para ello, necesitamos re-ejecutar el useEffect, una forma simple es:
      // (Mejor aún es definir fetchEmpresas fuera y usar useCallback, pero esto funciona)
      const fetchAgain = async () => {
         const res = await fetch(`${API_URL}/empresas/admin/lista`, { headers: { Authorization: `Bearer ${token}` } });
         setEmpresas(await res.json());
      }
      fetchAgain();
      setNombreLegal(""); setNombreFantasia(""); setCuit("");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Error al crear la empresa.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="p-6 space-y-8">
      {/* Modal de Configuración */}
      <Dialog open={!!empresaSeleccionada} onOpenChange={() => setEmpresaSeleccionada(null)}>
        <DialogContent className="sm:max-w-[625px]">
          <DialogHeader>
            <DialogTitle>Configurar Empresa: {empresaSeleccionada?.nombre_legal}</DialogTitle>
            <DialogDescription>
              Gestione los datos y credenciales de esta empresa.
            </DialogDescription>
          </DialogHeader>
          
          <div className="p-4 border rounded-lg">
            <h3 className="font-semibold">Datos Generales</h3>
            {/* ... Formulario para editar nombre, color, etc. ... */}
          </div>

          {empresaSeleccionada && <AfipWizard empresa={empresaSeleccionada} />}

          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">Cerrar</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Contenido Principal */}
      <div>
        <h1 className="text-2xl font-bold">Gestión de Empresas</h1>
        <p className="text-gray-500">Crea y administra las empresas clientes del sistema.</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          <form onSubmit={handleSubmit} className="space-y-4 p-4 border rounded-lg shadow-sm">
            <h2 className="text-lg font-semibold border-b pb-2">Añadir Nueva Empresa</h2>
            <div className="space-y-2">
              <Label htmlFor="nombreLegal">Nombre Legal / Razón Social</Label>
              <Input id="nombreLegal" value={nombreLegal} onChange={(e) => setNombreLegal(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="nombreFantasia">Nombre de Fantasía</Label>
              <Input id="nombreFantasia" value={nombreFantasia} onChange={(e) => setNombreFantasia(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cuit">CUIT (sin guiones)</Label>
              <Input id="cuit" value={cuit} onChange={(e) => setCuit(e.target.value)} required maxLength={11} />
            </div>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              <Loader2 className={`animate-spin mr-2 h-4 w-4 ${!isSubmitting && 'hidden'}`} />
              {isSubmitting ? "Creando..." : "Crear Empresa"}
            </Button>
          </form>
        </div>
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold mb-2">Empresas Registradas</h2>
          <div className="border rounded-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nombre Legal</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">CUIT</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {isLoadingList ? (
                  <tr><td colSpan={4} className="text-center py-8"><Loader2 className="animate-spin mx-auto text-gray-400" /></td></tr>
                ) : empresas.length === 0 ? (
                  <tr><td colSpan={4} className="text-center py-8 text-gray-500">No hay empresas registradas.</td></tr>
                ) : (
                  empresas.map((empresa) => (
                    <tr key={empresa.id}>
                      <td className="px-4 py-4 whitespace-nowrap text-sm font-medium">{empresa.nombre_legal}</td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm">{empresa.cuit}</td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${empresa.activa ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                          {empresa.activa ? 'Activa' : 'Inactiva'}
                        </span>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-center text-sm">
                        <Button variant="outline" size="sm" onClick={() => setEmpresaSeleccionada(empresa)}>
                          <Settings className="h-4 w-4 mr-2" />
                          Configurar
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}