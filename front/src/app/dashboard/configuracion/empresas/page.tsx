"use client";

import { useState, useEffect, FormEvent, ChangeEvent, Fragment, useCallback } from "react";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, Settings, FileKey, UploadCloud, Building, UserPlus } from "lucide-react";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription, 
  DialogFooter,
} from "@/components/ui/dialog";
import Image from "next/image";

// --- INTERFACES Y CONSTANTES ---
interface Empresa {
  id: number;
  nombre_legal: string;
  nombre_fantasia?: string;
  cuit: string;
  activa: boolean;
}

interface ConfiguracionEmpresa {
    id_empresa: number;
    nombre_negocio: string | null;
    color_principal: string;
    ruta_logo: string | null;
    ruta_icono: string | null;
    afip_condicion_iva: string | null;
    afip_punto_venta_predeterminado: number | null;
    direccion_negocio: string | null;
    telefono_negocio: string | null;
    mail_negocio: string | null;
}

const API_URL = "https://sistema-ima.sistemataup.online/api";

// ===================================================================
// === COMPONENTE AISLADO: ASISTENTE DE CREDENCIALES AFIP
// ===================================================================
function AfipWizard({ empresa }: { empresa: Empresa }) {
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

// ===================================================================
// === COMPONENTE AISLADO: MODAL DE CONFIGURACIÓN DE EMPRESA
// ===================================================================
function ConfiguracionModal({ empresa, onClose, onUpdated }: { empresa: Empresa; onClose: () => void; onUpdated: () => void; }) {
    const token = useAuthStore((state) => state.token);
    const [config, setConfig] = useState<ConfiguracionEmpresa | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const fetchConfig = useCallback(async () => {
        if (!token) return;
        setIsLoading(true);
        try {
            const res = await fetch(`${API_URL}/configuracion/empresa/${empresa.id}`, { headers: { Authorization: `Bearer ${token}` } });
            if (!res.ok) throw new Error("No se pudo cargar la configuración de la empresa.");
            setConfig(await res.json());
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Error desconocido.");
            onClose();
        } finally {
            setIsLoading(false);
        }
    }, [empresa.id, token, onClose]);

    useEffect(() => { fetchConfig(); }, [fetchConfig]);

    const handleUpdate = async (updateData: Partial<ConfiguracionEmpresa>) => {
        setIsLoading(true);
        try {
            const res = await fetch(`${API_URL}/configuracion/empresa/${empresa.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify(updateData),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail);
            setConfig(data);
            toast.success("Configuración guardada.");
            onUpdated();
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "No se pudo guardar la configuración.");
        } finally {
            setIsLoading(false);
        }
    };
    
    const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>, tipo: 'logo' | 'icono') => {
        if (!e.target.files?.[0]) return;
        const file = e.target.files[0];
        const formData = new FormData();
        formData.append('file', file);
        setIsLoading(true);
        try {
            const res = await fetch(`${API_URL}/configuracion/upload-logo/${empresa.id}`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
                body: formData,
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail);
            await fetchConfig();
            toast.success(`${tipo.charAt(0).toUpperCase() + tipo.slice(1)} subido con éxito.`);
        } catch (error) {
            toast.error(error instanceof Error ? error.message : `No se pudo subir el ${tipo}.`);
        } finally {
            setIsLoading(false);
        }
    };
    return (
    <Dialog open={true} onOpenChange={onClose}>
        <DialogContent className="sm:max-w-[625px]">
            <DialogHeader>
                <DialogTitle>Configurar Empresa: {empresa.nombre_legal}</DialogTitle>
                <DialogDescription>
                    Gestione los datos, apariencia y credenciales de esta empresa.
                </DialogDescription>
            </DialogHeader>

            {/* --- Estado de Carga --- */}
            {isLoading && (
                <div className="flex justify-center items-center p-8 min-h-[300px]">
                    <Loader2 className="animate-spin h-8 w-8 text-gray-400" />
                </div>
            )}

            {/* --- Contenido del Formulario --- */}
            {!isLoading && config && (
                <div className="space-y-6 py-4 max-h-[70vh] overflow-y-auto pr-2">
                    {/* Sección de Datos Generales */}
                    <div className="p-4 border rounded-lg space-y-4">
                        <h3 className="font-semibold text-lg">Datos Generales y de Contacto</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <Label htmlFor="nombre_negocio">Nombre del Negocio (para tickets)</Label>
                                <Input id="nombre_negocio" defaultValue={config.nombre_negocio || ''} onBlur={(e) => handleUpdate({ nombre_negocio: e.target.value })}/>
                            </div>
                            <div>
                                <Label htmlFor="direccion_negocio">Dirección del Negocio</Label>
                                <Input id="direccion_negocio" defaultValue={config.direccion_negocio || ''} onBlur={(e) => handleUpdate({ direccion_negocio: e.target.value })}/>
                            </div>
                            <div>
                                <Label htmlFor="telefono_negocio">Teléfono</Label>
                                <Input id="telefono_negocio" defaultValue={config.telefono_negocio || ''} onBlur={(e) => handleUpdate({ telefono_negocio: e.target.value })}/>
                            </div>
                            <div>
                                <Label htmlFor="mail_negocio">Email de Contacto</Label>
                                <Input id="mail_negocio" type="email" defaultValue={config.mail_negocio || ''} onBlur={(e) => handleUpdate({ mail_negocio: e.target.value })}/>
                            </div>
                        </div>
                    </div>

                    {/* Sección de Personalización */}
                    <div className="p-4 border rounded-lg space-y-4">
                        <h3 className="font-semibold text-lg">Personalización y Apariencia</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
                            <div>
                                <Label>Color Principal</Label>
                                <div className="flex items-center gap-2 mt-1">
                                    <Input id="color_principal" type="color" className="w-12 h-10 p-1" defaultValue={config.color_principal} onChange={(e) => handleUpdate({ color_principal: e.target.value })}/>
                                    <span className="text-sm text-gray-600">Color de la marca.</span>
                                </div>
                            </div>
                            <div>
                                <Label htmlFor="logo">Logo (para comprobantes PDF)</Label>
                                <Input id="logo" type="file" accept="image/png, image/jpeg, image/svg+xml" className="mt-1" onChange={(e) => handleFileUpload(e, 'logo')} />
                                {config.ruta_logo && (
                                    <div className="mt-2 p-2 border rounded bg-white inline-block">
                                        <div className="relative w-32 h-32">
                                            <Image 
                                                src={`${API_URL}${config.ruta_logo}`} 
                                                alt="Logo actual" 
                                                layout="fill" 
                                                objectFit="contain"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                            <div>
                                <Label htmlFor="icono">Icono (favicon)</Label>
                                <Input id="icono" type="file" accept="image/png, image/jpeg, image/svg+xml, image/x-icon" className="mt-1" onChange={(e) => handleFileUpload(e, 'icono')} />
                                {config.ruta_icono && (
                                    <div className="mt-2 p-2 border rounded bg-white inline-block">
                                        <div className="relative w-16 h-16">
                                            <Image 
                                                src={`${API_URL}${config.ruta_icono}`} 
                                                alt="Icono actual" 
                                                layout="fill" 
                                                objectFit="contain" 
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                    
                    {/* Asistente de AFIP */}
                    <AfipWizard empresa={empresa} />
                </div>
            )}

            <DialogFooter>
                <Button type="button" variant="secondary" onClick={onClose}>Cerrar</Button>
            </DialogFooter>
        </DialogContent>
    </Dialog>
);
}
// ===================================================================
// === COMPONENTE AISLADO: MODAL PARA CREAR PRIMER USUARIO ADMIN
// ===================================================================
function CreateAdminUserModal({ empresa, onClose, onUserCreated }: { empresa: Empresa; onClose: () => void; onUserCreated: () => void; }) {
    const token = useAuthStore((state) => state.token);
    const [nombreUsuario, setNombreUsuario] = useState("");
    const [password, setPassword] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!nombreUsuario || password.length < 8) {
            return toast.error("El nombre de usuario es obligatorio y la contraseña debe tener al menos 8 caracteres.");
        }
        setIsSubmitting(true);
        try {
            const newUserPayload = {
                nombre_usuario: nombreUsuario,
                password: password,
                nombre_rol: "Admin",
                id_empresa: empresa.id
            };

            const res = await fetch(`${API_URL}/admin/usuarios/crear`, {
                method: "POST",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify(newUserPayload),
            });
            const data = await res.json();
            if (!res.ok) {
            const errorMessage = (data && typeof data === 'object' && 'detail' in data) 
                ? (data as { detail: string }).detail 
                : "No se pudo crear la empresa.";
            throw new Error(errorMessage);
            }
            
            toast.success(`¡Usuario administrador "${nombreUsuario}" creado para ${empresa.nombre_legal}!`);
            onUserCreated();
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Error al crear el usuario.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <Dialog open={true} onOpenChange={onClose}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Crear Primer Usuario para {empresa.nombre_legal}</DialogTitle>
                    <DialogDescription>
                        Este será el usuario administrador principal para la empresa.
                    </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4 pt-4">
                    <div>
                        <Label htmlFor="adminUserName">Nombre de Usuario</Label>
                        <Input id="adminUserName" value={nombreUsuario} onChange={(e) => setNombreUsuario(e.target.value)} required />
                    </div>
                    <div>
                        <Label htmlFor="adminPassword">Contraseña Temporal</Label>
                        <Input id="adminPassword" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
                    </div>
                    <DialogFooter>
                        <Button type="button" variant="ghost" onClick={onClose}>Omitir por ahora</Button>
                        <Button type="submit" disabled={isSubmitting}>
                            <Loader2 className={`animate-spin mr-2 h-4 w-4 ${!isSubmitting && 'hidden'}`} />
                            Crear Usuario Admin
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}


// ===================================================================
// === COMPONENTE PRINCIPAL DE LA PÁGINA
// ===================================================================
export default function SuperAdminEmpresasPage() {
    const token = useAuthStore((state) => state.token);
    const [empresas, setEmpresas] = useState<Empresa[]>([]);
    const [isLoadingList, setIsLoadingList] = useState(true);
    const [nombreLegal, setNombreLegal] = useState("");
    const [nombreFantasia, setNombreFantasia] = useState("");
    const [cuit, setCuit] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    
    const [empresaParaConfig, setEmpresaParaConfig] = useState<Empresa | null>(null);
    const [empresaParaCrearUsuario, setEmpresaParaCrearUsuario] = useState<Empresa | null>(null);

    const fetchEmpresas = useCallback(async () => {
        if (!token) return;
        setIsLoadingList(true);
        try {
            const res = await fetch(`${API_URL}/empresas/admin/lista`, { headers: { Authorization: `Bearer ${token}` } });
            if (!res.ok) throw new Error("No se pudo cargar la lista de empresas.");
            setEmpresas(await res.json());
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Error al cargar empresas.");
        } finally {
            setIsLoadingList(false);
        }
    }, [token]);

    useEffect(() => { fetchEmpresas(); }, [fetchEmpresas]);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!nombreLegal || !cuit || cuit.length !== 11) return toast.error("Nombre Legal y un CUIT de 11 dígitos son obligatorios.");
        setIsSubmitting(true);
        try {
            const res = await fetch(`${API_URL}/empresas/admin/crear`, {
                method: "POST",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify({ nombre_legal: nombreLegal, nombre_fantasia: nombreFantasia || null, cuit }),
            });
            const data: Empresa = await res.json();
                  if (!res.ok) {
        // Creamos un "guardián" para comprobar de forma segura si el objeto de error
        // tiene la estructura que esperamos (un objeto con una clave 'detail').
            const errorMessage = (data && typeof data === 'object' && 'detail' in data) 
                ? String(data.detail) // Si tiene 'detail', usamos ese mensaje.
                : "No se pudo crear la empresa. Respuesta inesperada del servidor."; // Si no, usamos un mensaje genérico.
            
            throw new Error(errorMessage);
            }
            
            toast.success("¡Empresa creada! Ahora, crea su primer usuario administrador.");
            setNombreLegal(""); setNombreFantasia(""); setCuit("");
            await fetchEmpresas();
            setEmpresaParaCrearUsuario(data);

        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Error al crear la empresa.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="p-6 space-y-8">
            {empresaParaConfig && (
                <ConfiguracionModal 
                    empresa={empresaParaConfig}
                    onClose={() => setEmpresaParaConfig(null)}
                    onUpdated={fetchEmpresas}
                />
            )}
            {empresaParaCrearUsuario && (
                <CreateAdminUserModal
                    empresa={empresaParaCrearUsuario}
                    onClose={() => setEmpresaParaCrearUsuario(null)}
                    onUserCreated={() => {
                        toast.info("Proceso de alta de empresa finalizado.");
                        setEmpresaParaCrearUsuario(null);
                    }}
                />
            )}
            
            <div className="flex items-center gap-4">
                <Building size={32} />
                <div>
                    <h1 className="text-2xl font-bold">Panel de Super-Administrador: Gestión de Empresas</h1>
                    <p className="text-gray-500">Crea y configura las empresas clientes que utilizarán el sistema.</p>
                </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-1">
                  <form onSubmit={handleSubmit} className="space-y-4 p-4 border rounded-lg shadow-sm bg-white">
                    <h2 className="text-lg font-semibold border-b pb-2 flex items-center gap-2"><UserPlus size={20} /> Añadir Nueva Empresa</h2>
                    <div className="space-y-2">
                      <Label htmlFor="nombreLegal">Nombre Legal / Razón Social</Label>
                      <Input id="nombreLegal" value={nombreLegal} onChange={(e) => setNombreLegal(e.target.value)} required />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="nombreFantasia">Nombre de Fantasía (Opcional)</Label>
                      <Input id="nombreFantasia" value={nombreFantasia} onChange={(e) => setNombreFantasia(e.target.value)} />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="cuit">CUIT (sin guiones)</Label>
                      <Input id="cuit" value={cuit} onChange={(e) => setCuit(e.target.value)} required maxLength={11} />
                    </div>
                    <Button type="submit" className="w-full" disabled={isSubmitting}>
                      <Loader2 className={`animate-spin mr-2 h-4 w-4 ${!isSubmitting && 'hidden'}`} />
                      {isSubmitting ? "Creando..." : "Crear Empresa y Continuar"}
                    </Button>
                  </form>
                </div>
                <div className="lg:col-span-2">
                   <h2 className="text-lg font-semibold mb-2">Empresas Registradas</h2>
                   <div className="border rounded-lg overflow-hidden bg-white shadow-sm">
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
                                           <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{empresa.nombre_legal}</td>
                                           <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">{empresa.cuit}</td>
                                           <td className="px-4 py-4 whitespace-nowrap text-sm">
                                               <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${empresa.activa ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                                                 {empresa.activa ? 'Activa' : 'Inactiva'}
                                               </span>
                                           </td>
                                           <td className="px-4 py-4 whitespace-nowrap text-center text-sm">
                                               <Button variant="outline" size="sm" onClick={() => setEmpresaParaConfig(empresa)}>
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
