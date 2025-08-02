"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/authStore";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"; // Asumiendo que usas shadcn

// Función helper para descargar archivos desde el navegador
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

// Definimos la 'forma' de una empresa aquí para claridad
interface Empresa {
  id: number;
  nombre_legal: string;
  cuit: string;
}

export function AfipToolsPanel() {
  const token = useAuthStore((state) => state.token);
  const [empresas, setEmpresas] = React.useState<Empresa[]>([]);
  const [selectedEmpresa, setSelectedEmpresa] = React.useState<Empresa | null>(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState<string | null>(null);
  const [certificateFile, setCertificateFile] = React.useState<File | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Cargar la lista de empresas al montar el componente
  React.useEffect(() => {
    const fetchEmpresas = async () => {
      if (!token) return;
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/empresas/admin/lista", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("No se pudo cargar la lista de empresas.");
        const data = await res.json();
        setEmpresas(data);
      } catch (err) {
        if (err instanceof Error) setError(err.message);
      }
    };
    fetchEmpresas();
  }, [token]);

  const handleGenerateCSR = async () => {
    if (!selectedEmpresa) {
      setError("Por favor, selecciona una empresa primero.");
      return;
    }
    setIsLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/afip-tools/generar-csr", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          cuit: selectedEmpresa.cuit,
          razon_social: selectedEmpresa.nombre_legal,
        }),
      });
      if (!res.ok) throw new Error("Error al generar la solicitud (CSR).");
      
      const csrContent = await res.text();
      downloadFile(csrContent, `${selectedEmpresa.cuit}.csr`, "application/x-pem-file");
      setSuccess("¡Solicitud generada con éxito! El archivo .csr se ha descargado. Súbelo a la web de AFIP.");

    } catch (err) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadCertificate = async () => {
    if (!selectedEmpresa) {
      setError("Por favor, selecciona una empresa primero.");
      return;
    }
    if (!certificateFile) {
      setError("Por favor, selecciona un archivo .crt para subir.");
      return;
    }
    setIsLoading(true);
    setError(null);
    setSuccess(null);
    
    // Leemos el contenido del archivo como texto
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
            const errorData = await res.json();
            throw new Error(errorData.detail || "Error al subir el certificado.");
        }
        setSuccess("¡Certificado subido y credenciales guardadas con éxito!");
        // Limpiamos el input
        if (fileInputRef.current) fileInputRef.current.value = "";
        setCertificateFile(null);
      } catch (err) {
        if (err instanceof Error) setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };
    reader.onerror = () => {
      setError("Error al leer el archivo del certificado.");
      setIsLoading(false);
    };
  };

  return (
    <div className="border rounded-lg p-6 space-y-8 bg-slate-50">
      <h2 className="text-xl font-bold">Herramientas de Credenciales AFIP</h2>
      
      {error && <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded-md">{error}</div>}
      {success && <div className="p-3 bg-green-100 border border-green-400 text-green-700 rounded-md">{success}</div>}
      
      {/* --- Selección de Empresa --- */}
      <div className="space-y-2">
        <label className="font-medium">1. Selecciona la Empresa</label>
        <Select onValueChange={(value) => setSelectedEmpresa(empresas.find(e => e.id === parseInt(value)) || null)}>
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

      {/* --- Acciones (se habilitan al seleccionar una empresa) --- */}
      <div className={`transition-opacity duration-300 ${!selectedEmpresa ? 'opacity-50 pointer-events-none' : 'opacity-100'}`}>
        <div className="border-t pt-6 space-y-2">
          <label className="font-medium">2. Generar Solicitud de Certificado</label>
          <p className="text-sm text-muted-foreground">
            Esto genera la clave privada (se queda en el servidor) y te da el archivo `.csr` para subir a AFIP.
          </p>
          <Button onClick={handleGenerateCSR} disabled={isLoading || !selectedEmpresa}>
            {isLoading ? "Generando..." : "Generar y Descargar .csr"}
          </Button>
        </div>
        
        <div className="border-t pt-6 mt-6 space-y-2">
          <label className="font-medium">3. Subir Certificado Firmado por AFIP</label>
          <p className="text-sm text-muted-foreground">
            Una vez que AFIP te devuelva el certificado (`.crt`), súbelo aquí para completar.
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