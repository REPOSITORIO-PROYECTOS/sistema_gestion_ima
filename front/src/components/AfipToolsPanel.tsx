"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/authStore";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

// Función helper para descargar archivos (sin cambios, es correcta)
const downloadFile = (content: string, fileName: string, contentType: string) => {
  const a = document.createElement("a");
  const file = new Blob([content], { type: contentType });
  a.href = URL.createObjectURL(file);
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
};

// Definimos un tipo explícito para la respuesta de la API de lista de empresas
interface Empresa {
  id: number;
  nombre_legal: string;
  cuit: string;
}

// Definimos las props que este componente puede recibir
interface AfipToolsPanelProps {
  empresaId?: number; // Es opcional, para pre-seleccionar una empresa
}

export function AfipToolsPanel({ empresaId }: AfipToolsPanelProps) {
  const token = useAuthStore((state) => state.token);
  const [empresas, setEmpresas] = React.useState<Empresa[]>([]);
  const [selectedEmpresa, setSelectedEmpresa] = React.useState<Empresa | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [certificateFile, setCertificateFile] = React.useState<File | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    const fetchEmpresas = async () => {
      if (!token) return;
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/empresas/admin/lista", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("No se pudo cargar la lista de empresas.");
        
        // Aserción de tipo: Le decimos a TypeScript que confiamos en que la respuesta es un array de Empresas
        const data = await res.json() as Empresa[];
        setEmpresas(data);

        // Si se pasó un empresaId, la pre-seleccionamos
        if (empresaId) {
          const initialEmpresa = data.find(e => e.id === empresaId);
          if (initialEmpresa) {
            setSelectedEmpresa(initialEmpresa);
          }
        }
      } catch (err) {
        // Manejo de errores seguro, verificando el tipo de 'err'
        if (err instanceof Error) {
          toast.error("Error al cargar empresas", { description: err.message });
        }
      }
    };
    fetchEmpresas();
  }, [token, empresaId]);

  const handleGenerateCSR = async () => {
    if (!selectedEmpresa) {
      toast.warning("Por favor, selecciona una empresa primero.");
      return;
    }
    setIsLoading(true);
    toast.info("Generando solicitud de certificado...");

    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/afip-tools/generar-csr", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          cuit: selectedEmpresa.cuit,
          razon_social: selectedEmpresa.nombre_legal,
        }),
      });
      if (!res.ok) {
        const errorData = await res.json() as { detail: string };
        throw new Error(errorData.detail || "Error del servidor al generar la solicitud (CSR).");
      }
      
      const csrContent = await res.text();
      downloadFile(csrContent, `${selectedEmpresa.cuit}.csr`, "application/x-pem-file");
      toast.success("¡Solicitud generada con éxito!", { description: "El archivo .csr se ha descargado." });

    } catch (err) {
      if (err instanceof Error) toast.error("Error en la generación", { description: err.message });
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadCertificate = async () => {
    if (!selectedEmpresa || !certificateFile) {
      toast.warning("Por favor, selecciona una empresa y un archivo .crt.");
      return;
    }
    setIsLoading(true);
    toast.info("Subiendo y guardando certificado...");
    
    const reader = new FileReader();
    reader.readAsText(certificateFile);
    reader.onload = async () => {
      const certificatePEM = reader.result as string;
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/afip-tools/subir-certificado", {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            cuit: selectedEmpresa.cuit,
            certificado_pem: certificatePEM,
          }),
        });
        if (!res.ok) {
            const errorData = await res.json() as { detail: string };
            throw new Error(errorData.detail || "Error al subir el certificado.");
        }
        toast.success("¡Certificado guardado con éxito en la bóveda!");
        if (fileInputRef.current) fileInputRef.current.value = "";
        setCertificateFile(null);
      } catch (err) {
        if (err instanceof Error) toast.error("Error al subir certificado", { description: err.message });
      } finally {
        setIsLoading(false);
      }
    };
    reader.onerror = () => {
      toast.error("Error crítico al leer el archivo del certificado.");
      setIsLoading(false);
    };
  };

  return (
    <div className="border rounded-lg p-6 space-y-8 bg-slate-50">
      <h2 className="text-xl font-bold">Herramientas de Credenciales AFIP</h2>
      
      <div className="space-y-2">
        <label className="font-medium">1. Selecciona la Empresa</label>
        <Select
          value={selectedEmpresa?.id.toString()}
          onValueChange={(value) => setSelectedEmpresa(empresas.find(e => e.id === parseInt(value)) || null)}
          disabled={!!empresaId} // Se deshabilita si la empresa viene pre-seleccionada
        >
          <SelectTrigger><SelectValue placeholder="Seleccionar una empresa..." /></SelectTrigger>
          <SelectContent>
            {empresas.map(empresa => (
              <SelectItem key={empresa.id} value={empresa.id.toString()}>
                {empresa.nombre_legal} (CUIT: {empresa.cuit})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className={`transition-opacity duration-300 ${!selectedEmpresa ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
        <div className="border-t pt-6 space-y-2">
          <label className="font-medium">2. Generar Solicitud de Certificado</label>
          <p className="text-sm text-muted-foreground">
            Genera la clave privada (se guarda en el servidor) y descarga el `.csr` para subir a AFIP.
          </p>
          <Button onClick={handleGenerateCSR} disabled={isLoading || !selectedEmpresa}>
            {isLoading ? "Generando..." : "Generar y Descargar .csr"}
          </Button>
        </div>
        
        <div className="border-t pt-6 mt-6 space-y-2">
          <label className="font-medium">3. Subir Certificado Firmado por AFIP</label>
          <p className="text-sm text-muted-foreground">
            Una vez que AFIP te devuelva el `.crt`, súbelo aquí para guardarlo en la bóveda segura.
          </p>
          <div className="flex items-center gap-4">
            <Input 
              ref={fileInputRef}
              type="file" 
              accept=".crt" 
              onChange={(e) => setCertificateFile(e.target.files ? e.target.files[0] : null)}
              className="flex-grow"
              disabled={isLoading || !selectedEmpresa}
            />
            <Button onClick={handleUploadCertificate} disabled={isLoading || !selectedEmpresa || !certificateFile}>
              {isLoading ? "Procesando..." : "Subir .crt"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}