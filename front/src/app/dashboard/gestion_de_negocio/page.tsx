'use client';

import { useFacturacionStore } from '@/lib/facturacionStore';
import * as Switch from '@radix-ui/react-switch';
import { Input } from "@/components/ui/input";
import { useEffect, useRef, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuthStore } from '@/lib/authStore';
import { toast } from 'sonner';
import { ConfiguracionForm } from "@/components/ConfiguracionForm";
import { useEmpresaStore } from '@/lib/empresaStore';
import ProtectedRoute from '@/components/ProtectedRoute';
import eventBus from "@/utils/eventBus";
import { Button } from '@/components/ui/button';
import { useCustomLinksStore } from '@/lib/customLinksStore';
import { API_CONFIG } from '@/lib/api-config';
import { AfipToolsPanel } from '@/components/AfipToolsPanel';
import { NavigationMenu, NavigationMenuList, NavigationMenuItem, NavigationMenuLink } from "@/components/ui/navigation-menu";
import { useFeaturesStore } from "@/lib/featuresStore";
import { useRouter as useNextRouter } from "next/navigation";

export default function GestionNegocio() {

  const token = useAuthStore((state) => state.token);
  const {
    habilitarExtras,
    toggleExtras,
    recargoTransferenciaActivo,
    toggleRecargoTransferencia,
    recargoTransferencia,
    setRecargoTransferencia,
    recargoBancarioActivo,
    toggleRecargoBancario,
    recargoBancario,
    setRecargoBancario,
    formatoComprobante,
    setFormatoComprobante
  } = useFacturacionStore();
  const [navbarColor, setNavbarColor] = useState("bg-sky-600");

  // Formatos de impresión de ticket - escalable a mas opciones 
  const formatosDisponibles = ["PDF", "Ticket"];

  /* Edición y manejo de empresas - obtenemos la empresa a partir del user para una cosa*/
  const usuario = useAuthStore((state) => state.usuario);
  const empresaId = usuario?.id_empresa;

  console.log("Usuario:", usuario);
  console.log("Empresa ID:", empresaId);

  // Edición de UI de empresa
  /* const [navbarColor, setNavbarColor] = useState("default"); */
  const fileInputRef = useRef<HTMLInputElement>(null);

  /* const logoUrl = empresa?.ruta_logo || '/default-logo.png'; */


  /* Manejo de Negocio y Ventas */

  // GET Recargos transferencia y banco
  useEffect(() => {
    if (!token) return;

    const fetchRecargos = async () => {
      try {
        const [resTransferencia, resBancario] = await Promise.all([
          fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa/recargo/transferencia`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa/recargo/banco`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        const dataTransferencia = await resTransferencia.json();
        const dataBancario = await resBancario.json();

        setRecargoTransferencia(dataTransferencia.porcentaje || 0);
        setRecargoBancario(dataBancario.porcentaje || 0);

      } catch (error) {
        console.error("Error al obtener recargos:", error);
      }
    };

    fetchRecargos();
  }, [token, setRecargoBancario, setRecargoTransferencia]);

  // GET Configuración General (para ancho ticket cambio)
  const [ticketCambioAncho, setTicketCambioAncho] = useState("80mm");
  const [ticketCambioHabilitado, setTicketCambioHabilitado] = useState(false);
  const [ticketCambioDias, setTicketCambioDias] = useState(30);

  useEffect(() => {
    if (!token) return;
    const fetchConfig = async () => {
      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          const aclaraciones = data.aclaraciones_legales || {};
          if (aclaraciones.ticket_cambio_ancho) {
            setTicketCambioAncho(aclaraciones.ticket_cambio_ancho);
          }
          if (aclaraciones.ticket_cambio_habilitado !== undefined) {
            const isEnabled = aclaraciones.ticket_cambio_habilitado === "true" || aclaraciones.ticket_cambio_habilitado === true;
            setTicketCambioHabilitado(isEnabled);
          }
          if (aclaraciones.ticket_cambio_plazo) {
            const dias = parseInt(String(aclaraciones.ticket_cambio_plazo), 10);
            if (!Number.isNaN(dias) && dias > 0) {
              setTicketCambioDias(dias);
            }
          }
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchConfig();
  }, [token]);

  // Guardar Ancho Ticket Cambio
  const guardarAnchoTicket = async (valor: string) => {
    setTicketCambioAncho(valor);
    if (!token || !empresaId) return;
    try {
      // 1. Obtener config actual para no sobrescribir otros campos de aclaraciones_legales
      const resGet = await fetch(`${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resGet.ok) throw new Error("No se pudo leer la configuración actual");

      const data = await resGet.json();
      const aclaraciones = data.aclaraciones_legales || {};

      // 2. Patch con el nuevo valor
      const res = await fetch(`${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          aclaraciones_legales: {
            ...aclaraciones,
            ticket_cambio_ancho: valor
          }
        })
      });

      if (res.ok) {
        toast.success("Ancho de ticket actualizado");
      } else {
        toast.error("Error al guardar configuración");
      }
    } catch (e) {
      console.error(e);
      toast.error("Error al guardar configuración");
    }
  };

  const guardarTicketCambioHabilitado = async (valor: boolean) => {
    setTicketCambioHabilitado(valor);
    if (!token || !empresaId) return;
    try {
      const resGet = await fetch(`${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resGet.ok) throw new Error("Error al leer config");

      const data = await resGet.json();
      const aclaraciones = data.aclaraciones_legales || {};

      const res = await fetch(`${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          aclaraciones_legales: {
            ...aclaraciones,
            ticket_cambio_habilitado: valor ? "true" : "false"
          }
        })
      });

      if (res.ok) {
        toast.success(valor ? "✅ Ticket de cambio habilitado" : "❌ Ticket de cambio deshabilitado");
      } else {
        toast.error("Error al guardar configuración");
      }
    } catch (e) {
      console.error(e);
      toast.error("Error al guardar configuración");
    }
  };

  const guardarTicketCambioDias = async (valor: number) => {
    setTicketCambioDias(valor);
    if (!token || !empresaId) return;
    try {
      const resGet = await fetch(`${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resGet.ok) throw new Error("Error al leer config");

      const data = await resGet.json();
      const aclaraciones = data.aclaraciones_legales || {};

      const res = await fetch(`${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          aclaraciones_legales: {
            ...aclaraciones,
            ticket_cambio_plazo: String(valor)
          }
        })
      });

      if (res.ok) {
        toast.success("Plazo de ticket de cambio actualizado");
      } else {
        toast.error("Error al guardar configuración");
      }
    } catch (e) {
      console.error(e);
      toast.error("Error al guardar configuración");
    }
  };

  // PATCH Recargos transferencia
  const actualizarRecargoTransferencia = async () => {
    try {
      const res = await fetch(
        `${API_CONFIG.BASE_URL}/configuracion/mi-empresa/recargo/transferencia`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            porcentaje: recargoTransferencia,
            concepto: "Actualización recargo transferencia"
          }),
        }
      );

      if (!res.ok) throw new Error("Error en el PATCH");
      toast.success("Recargo por transferencia actualizado correctamente");

    } catch (error) {
      console.error(error);
      toast.error("Error al actualizar el recargo por transferencia");
    }
  };

  // PATCH Recargos banco
  const actualizarRecargoBancario = async () => {
    try {
      const res = await fetch(
        `${API_CONFIG.BASE_URL}/configuracion/mi-empresa/recargo/banco`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            porcentaje: recargoBancario,
            concepto: "Actualización recargo bancario"
          }),
        }
      );

      if (!res.ok) throw new Error("Error en el PATCH");

      toast.success("Recargo por banco actualizado correctamente");

    } catch (error) {
      console.error(error);
      toast.error("Error al actualizar el recargo por banco");
    }
  };

  /* UI */

  /* Utilizamos el empresaStore para otras, como editar la UI */
  // Subir LOGO al Back para personalización
  const subirArchivo = async (file: File) => {
    if (!token) throw new Error("Token no disponible");

    const formData = new FormData();
    formData.append("archivo", file);

    const res = await fetch(`${API_CONFIG.BASE_URL}/configuracion/upload-logo`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "Error al subir el archivo");

    return data;
  };

  // Handler para cambiar el LOGO de la empresa
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ["image/png", "image/jpeg", "image/webp"];
    if (!allowedTypes.includes(file.type)) {
      toast.error("Formato no permitido. Solo .png, .jpg, .webp");
      return;
    }

    if (!token) {
      toast.error("No hay token de sesión, vuelva a iniciar sesión");
      return;
    }

    try {
      const { message } = await subirArchivo(file);
      console.log(message);

      // Refrescar datos actualizados desde el backend
      const res = await fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const data = await res.json();
      useEmpresaStore.getState().setEmpresa(data);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      toast.success("Logo subido correctamente.");
      eventBus.emit("empresa_actualizada");

      window.location.reload();

    } catch (error) {
      console.error(error);
      toast.error("Error al subir el logo");
    }
  };

  // Funcion para cambiar de color
  const actualizarColorNavbar = async (nuevoColor: string) => {
    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa/color", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ color_principal: nuevoColor }),
      });

      if (!res.ok) throw new Error("Error en el PATCH");

      toast.success("Color de navbar actualizado correctamente.");
      eventBus.emit("empresa_actualizada");

    } catch (error) {
      console.error(error);
      toast.error("Error al actualizar el color de navbar");
    }
  };


  // ESTADO Y MANEJO DE ENLACES PERSONALIZADOS
  const [link1, setLink1] = useState('');
  const [link2, setLink2] = useState('');
  const [link3, setLink3] = useState('');
  const [name1, setName1] = useState('Enlace 1');
  const [name2, setName2] = useState('Enlace 2');
  const [name3, setName3] = useState('Enlace 3');

  const setCustomLink = useCustomLinksStore((s) => s.setLink);
  const customLinks = useCustomLinksStore((s) => s.links);
  const setVisibility = useCustomLinksStore((s) => s.setVisibility);
  const removeLink = useCustomLinksStore((s) => s.removeLink);
  const [visible1, setVisible1] = useState(true);
  const [visible2, setVisible2] = useState(true);
  const [visible3, setVisible3] = useState(true);
  const mesasEnabled = useFeaturesStore((s) => s.mesasEnabled);
  const setMesasEnabled = useFeaturesStore((s) => s.setMesasEnabled);
  const nextRouter = useNextRouter();

  // Cargamos los enlaces al iniciar el componente
  useEffect(() => {
    if (!token) return;

    const fetchLinks = async () => {
      try {
        const [resLink1, resLink2, resLink3] = await Promise.all([
          fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa/link/1`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa/link/2`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa/link/3`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        const dataLink1 = await resLink1.json();
        const dataLink2 = await resLink2.json();
        const dataLink3 = await resLink3.json();

        setLink1(dataLink1.link || '');
        setLink2(dataLink2.link || '');
        setLink3(dataLink3.link || '');

        const stored = customLinks;
        const l1 = stored.find((l) => l.id === 1);
        const l2 = stored.find((l) => l.id === 2);
        const l3 = stored.find((l) => l.id === 3);
        setName1(l1?.name || 'Enlace 1');
        setName2(l2?.name || 'Enlace 2');
        setName3(l3?.name || 'Enlace 3');
        setVisible1(l1?.visible ?? true);
        setVisible2(l2?.visible ?? true);
        setVisible3(l3?.visible ?? true);

      } catch (error) {
        console.error("Error al obtener los enlaces:", error);
        toast.error("Error al obtener los enlaces personalizados.");
      }
    };

    fetchLinks();
  }, [token, customLinks]);

  useEffect(() => {
    if (!token || !empresaId) return;
    const cargarIntegraciones = async () => {
      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
        });
        if (!res.ok) return;
        const data = await res.json();
        const val = (data.aclaraciones_legales?.mesas_enabled ?? "false") === "true";
        setMesasEnabled(val);
      } catch { }
    };
    cargarIntegraciones();
  }, [token, empresaId, setMesasEnabled]);

  // Handler para guardar/actualizar un link (PATCH)
  const handleLinkSave = async (linkNumber: number, url: string) => {
    if (!token) {
      toast.error("No hay token de sesión, vuelva a iniciar sesión");
      return;
    }
    if (!url.trim()) {
      toast.error("El enlace no puede estar vacío.");
      return;
    }

    try {
      const res = await fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa/link/${linkNumber}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ link: url }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.message || "Error al guardar el enlace");
      }

      if (linkNumber === 1) setCustomLink(1, { name: name1, url });
      if (linkNumber === 2) setCustomLink(2, { name: name2, url });
      if (linkNumber === 3) setCustomLink(3, { name: name3, url });

      toast.success(`Enlace ${linkNumber} guardado correctamente.`);

    } catch (error) {
      console.error(`Error al guardar el enlace ${linkNumber}:`, error);
      toast.error(`Error al guardar el enlace ${linkNumber}`);
    }
  };

  const handleLinkDelete = async (linkNumber: number) => {
    if (!token) {
      toast.error("No hay token de sesión, vuelva a iniciar sesión");
      return;
    }
    try {
      const res = await fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa/link/${linkNumber}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ link: null }),
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.message || "Error al eliminar el enlace");
      }
      removeLink(linkNumber as 1 | 2 | 3);
      if (linkNumber === 1) { setLink1(''); setName1('Enlace 1'); setVisible1(false); }
      if (linkNumber === 2) { setLink2(''); setName2('Enlace 2'); setVisible2(false); }
      if (linkNumber === 3) { setLink3(''); setName3('Enlace 3'); setVisible3(false); }
      toast.success(`Enlace ${linkNumber} eliminado.`);
    } catch (error) {
      console.error(error);
      toast.error(`Error al eliminar el enlace ${linkNumber}`);
    }
  };


  const [activeTab, setActiveTab] = useState<'negocio' | 'personalizacion' | 'integraciones'>('negocio');

  return (
    <ProtectedRoute allowedRoles={["Admin", "Soporte"]}>
      <div className="flex flex-col gap-6 p-2">

        <NavigationMenu className="mb-4">
          <NavigationMenuList>
            <NavigationMenuItem>
              <NavigationMenuLink
                className={`px-4 py-2 rounded-t-md text-gray-700 hover:bg-gray-100 transition-colors duration-200
                  ${activeTab === 'negocio' ? 'bg-gradient-to-b from-green-100 to-green-200 text-green-800 font-semibold border-b-4 border-green-800' : ''}`}
                onClick={() => setActiveTab('negocio')}
              >
                Negocio y Fiscales
              </NavigationMenuLink>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuLink
                className={`px-4 py-2 rounded-t-md text-gray-700 hover:bg-gray-100 transition-colors duration-200
                  ${activeTab === 'personalizacion' ? 'bg-gradient-to-b from-green-100 to-green-200 text-green-800 font-semibold border-b-4 border-green-800' : ''}`}
                onClick={() => setActiveTab('personalizacion')}
              >
                Personalización
              </NavigationMenuLink>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuLink
                className={`px-4 py-2 rounded-t-md text-gray-700 hover:bg-gray-100 transition-colors duration-200
                  ${activeTab === 'integraciones' ? 'bg-gradient-to-b from-green-100 to-green-200 text-green-800 font-semibold border-b-4 border-green-800' : ''}`}
                onClick={() => setActiveTab('integraciones')}
              >
                Integraciones
              </NavigationMenuLink>
            </NavigationMenuItem>
          </NavigationMenuList>
        </NavigationMenu>



        {activeTab === 'negocio' && (
          <>
            {empresaId && (
              <>
                <ConfiguracionForm empresaId={empresaId} sections={{ general: true, balanza: false, afip: true }} />
                <div className="mt-8">
                  <h3 className="text-lg font-semibold text-green-900 mb-4">Herramientas AFIP</h3>
                  <AfipToolsPanel empresaId={empresaId} />
                </div>
              </>
            )}
            <hr className="h-0.25 my-4" />
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-green-950">Configuración sobre métodos de pago</h2>
              <p className="text-muted-foreground">Administrá el tipo de ticket para imprimir.</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Formato del Comprobante</label>
              <Select value={formatoComprobante} onValueChange={setFormatoComprobante}>
                <SelectTrigger className="w-[180px] cursor-pointer">
                  <SelectValue placeholder="Seleccionar formato" />
                </SelectTrigger>
                <SelectContent>
                  {formatosDisponibles.map((formato) => (
                    <SelectItem key={formato} value={formato}>
                      {formato}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <Switch.Root
                disabled={formatoComprobante !== "PDF"}
                checked={habilitarExtras}
                onCheckedChange={toggleExtras}
                className={`relative w-16 h-8 rounded-full ${habilitarExtras ? "bg-green-900" : "bg-gray-300"} cursor-pointer transition-colors ${formatoComprobante !== "PDF" ? "opacity-50 cursor-not-allowed" : ""}`}
              >
                <Switch.Thumb
                  className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${habilitarExtras ? "translate-x-8" : "translate-x-0"}`}
                />
              </Switch.Root>
              <h3 className="text-lg font-semibold text-green-950">Habilitar Remito / Presupuesto</h3>
            </div>
            <hr className="h-0.25 my-4" />
            <div className="space-y-2">
              <h2 className="text-xl font-bold text-green-950">Recargos asociados a métodos de pago.</h2>
              <p className="text-muted-foreground md:max-w-1/2">Desde acá podes asignar recargos a las opciones de transferencia o pago bancario. El valor que ves es el recargo actual, podes reemplazarlo y setear uno nuevo.</p>
            </div>
            <div className="flex flex-col gap-2">
              <div className="flex flex-col sm:flex-row items-center gap-4">
                <Switch.Root
                  checked={recargoTransferenciaActivo}
                  onCheckedChange={toggleRecargoTransferencia}
                  className={`relative w-16 h-8 rounded-full ${recargoTransferenciaActivo ? "bg-green-900" : "bg-gray-300"} cursor-pointer transition-colors`}
                >
                  <Switch.Thumb
                    className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${recargoTransferenciaActivo ? "translate-x-8" : "translate-x-0"}`}
                  />
                </Switch.Root>
                <h3 className="text-lg font-semibold text-green-950">Habilitar Recargo por Transferencia</h3>
              </div>
              <Input type="number" placeholder="Ej: 10" disabled={!recargoTransferenciaActivo} value={recargoTransferencia} onChange={(e) => {
                const rawValue = e.target.value;
                if (rawValue === "") return setRecargoTransferencia(0);
                const val = Number(rawValue);
                if (val >= 0 && val <= 100) setRecargoTransferencia(val);
              }} className="w-full md:w-1/3 mt-2" />
              <Button onClick={actualizarRecargoTransferencia} disabled={!recargoTransferenciaActivo} className="w-full md:w-1/3 bg-green-900 text-white px-4 py-1 rounded mt-2 disabled:opacity-50 transition">
                Guardar recargo transferencia
              </Button>
            </div>
            <hr className="h-0.25 my-4" />
            <div className="flex flex-col gap-2">
              <div className="flex flex-col sm:flex-row items-center gap-4">
                <Switch.Root
                  checked={recargoBancarioActivo}
                  onCheckedChange={toggleRecargoBancario}
                  className={`relative w-16 h-8 rounded-full ${recargoBancarioActivo ? "bg-green-900" : "bg-gray-300"} cursor-pointer transition-colors`}
                >
                  <Switch.Thumb
                    className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${recargoBancarioActivo ? "translate-x-8" : "translate-x-0"}`}
                  />
                </Switch.Root>
                <h3 className="text-lg font-semibold text-green-950">Habilitar Recargo por Bancario</h3>
              </div>
              <Input type="number" placeholder="Ej: 10" disabled={!recargoBancarioActivo} value={recargoBancario} onChange={(e) => {
                const rawValue = e.target.value;
                if (rawValue === "") return setRecargoBancario(0);
                const val = Number(rawValue);
                if (val >= 0 && val <= 100) setRecargoBancario(val);
              }} className="w-full md:w-1/3 mt-2" />
              <Button onClick={actualizarRecargoBancario} disabled={!recargoBancarioActivo} className="w-full md:w-1/3 bg-green-900 text-white px-4 py-1 rounded mt-2 disabled:opacity-50 transition">
                Guardar recargo bancario
              </Button>
            </div>
          </>
        )}



        {activeTab === 'personalizacion' && (
          <>
            <div className="flex flex-col items-start gap-8 p-4">
              <div className="space-y-2">
                <h2 className="text-xl font-bold text-green-950">Configuración de la Apariencia.</h2>
                <p className="text-muted-foreground">Administrá la apariencia de tu aplicación.</p>
              </div>
              <div className="flex flex-col sm:flex-row w-full md:w-1/2 items-start gap-8 mb-6">
                <label className="text-lg font-semibold text-green-950">🖌️ Personalizá el color de tu empresa:</label>
                <Select value={navbarColor} onValueChange={(val) => { setNavbarColor(val); actualizarColorNavbar(val); }}>
                  <SelectTrigger className="w-full cursor-pointer">
                    <SelectValue placeholder="Color del Navbar" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bg-sky-600">Colores:</SelectItem>
                    <SelectItem value="bg-green-800">Verde</SelectItem>
                    <SelectItem value="bg-emerald-700">Verde Claro</SelectItem>
                    <SelectItem value="bg-blue-900">Azul</SelectItem>
                    <SelectItem value="bg-sky-400">Azul Claro</SelectItem>
                    <SelectItem value="bg-red-700">Rojo</SelectItem>
                    <SelectItem value="bg-red-600">Rojo Claro</SelectItem>
                    <SelectItem value="bg-yellow-600">Amarillo</SelectItem>
                    <SelectItem value="bg-amber-300">Amarillo Claro</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col sm:flex-row w-full md:w-1/2 items-start gap-8 mb-6">
                <label className="text-lg font-semibold text-green-950">🎨 Cambiar logo de empresa:</label>
                <Input type="file" accept=".png,.jpg,.jpeg,.webp" ref={fileInputRef} onChange={handleFileChange} className="max-w-sm" />
              </div>

              <div className="flex flex-col gap-2 w-full md:w-1/2 mb-6">
                <div className="flex flex-col sm:flex-row items-center gap-4">
                  <Switch.Root
                    checked={ticketCambioHabilitado}
                    onCheckedChange={guardarTicketCambioHabilitado}
                    className={`relative w-16 h-8 rounded-full ${ticketCambioHabilitado ? "bg-green-900" : "bg-gray-300"} cursor-pointer transition-colors`}
                  >
                    <Switch.Thumb
                      className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${ticketCambioHabilitado ? "translate-x-8" : "translate-x-0"}`}
                    />
                  </Switch.Root>
                  <h3 className="text-lg font-semibold text-green-950">🎟️ Emitir Ticket de Cambio en cada venta</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  Cuando está habilitado, cada venta generará automáticamente <strong>dos comprobantes</strong>: el comprobante normal + un ticket de cambio con la fecha y monto del cambio.
                </p>
              </div>

              <div className="flex flex-col gap-2 w-full md:w-1/2 mb-6">
                <div className="flex flex-col sm:flex-row items-center gap-4">
                  <label className="text-lg font-semibold text-green-950 whitespace-nowrap">📅 Vigencia Ticket de Cambio (días):</label>
                  <Input
                    type="number"
                    min={1}
                    value={ticketCambioDias}
                    onChange={(e) => {
                      const raw = e.target.value;
                      const val = parseInt(raw, 10);
                      if (Number.isNaN(val)) return;
                      setTicketCambioDias(val);
                    }}
                    onBlur={(e) => {
                      const raw = e.target.value;
                      const val = parseInt(raw, 10);
                      if (Number.isNaN(val) || val <= 0) {
                        setTicketCambioDias(30);
                        guardarTicketCambioDias(30);
                        return;
                      }
                      guardarTicketCambioDias(val);
                    }}
                    disabled={!ticketCambioHabilitado}
                    className="w-full md:max-w-[180px]"
                  />
                </div>
                <p className="text-sm text-muted-foreground">
                  Se guarda en la base de datos y aplica al cálculo de fecha límite del ticket.
                </p>
              </div>

              <div className="flex flex-col gap-2 w-full md:w-1/2 mb-6">
                <div className="flex flex-col sm:flex-row items-center gap-4">
                  <label className="text-lg font-semibold text-green-950 whitespace-nowrap">🖨️ Ancho Ticket de Cambio:</label>
                  <Select value={ticketCambioAncho} onValueChange={guardarAnchoTicket} disabled={!ticketCambioHabilitado}>
                    <SelectTrigger className="w-full cursor-pointer">
                      <SelectValue placeholder="Seleccionar ancho" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="80mm">80mm (Estándar)</SelectItem>
                      <SelectItem value="58mm">58mm (Pequeña)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <p className="text-sm text-muted-foreground">
                  Esta configuración aplica <strong>únicamente</strong> al ticket de cambio. El comprobante principal mantiene su formato estándar.
                </p>
              </div>
            </div>
            <div className="flex flex-col items-start gap-8 p-4">
              <div className="space-y-2">
                <h2 className="text-xl font-bold text-green-950">Enlaces Personalizados.</h2>
                <p className="text-muted-foreground">Configurá enlaces externos para acceso rápido.</p>
              </div>
              <div className="flex flex-col w-full md:w-1/2 gap-2">
                <label className="text-lg font-semibold text-green-950">🔗 Enlace 1:</label>
                <Input type="url" placeholder="https://ejemplo.com" value={link1} onChange={(e) => setLink1(e.target.value)} className="w-full" />
                <Input type="text" placeholder="Nombre para Enlace 1" value={name1} onChange={(e) => setName1(e.target.value)} className="w-full" />
                <div className="flex gap-2 mt-2">
                  <Button onClick={() => handleLinkSave(1, link1)} className="bg-green-800 text-white px-4 py-1 rounded transition">Guardar Enlace 1</Button>
                  <Button onClick={() => handleLinkDelete(1)} className="bg-red-700 text-white px-4 py-1 rounded transition">Eliminar Enlace 1</Button>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <Switch.Root checked={visible1} onCheckedChange={(v) => { setVisible1(!!v); setVisibility(1, !!v); }} className={`relative w-14 h-7 rounded-full ${visible1 ? "bg-green-900" : "bg-gray-300"} cursor-pointer transition-colors`}>
                    <Switch.Thumb className={`absolute top-1 left-1 w-5 h-5 bg-white rounded-full shadow-md transition-transform duration-300 ${visible1 ? "translate-x-7" : "translate-x-0"}`} />
                  </Switch.Root>
                  <span className="text-sm">Mostrar en Navbar</span>
                </div>
              </div>
              <div className="flex flex-col w-full md:w-1/2 gap-2">
                <label className="text-lg font-semibold text-green-950">🔗 Enlace 2:</label>
                <Input type="url" placeholder="https://ejemplo2.com" value={link2} onChange={(e) => setLink2(e.target.value)} className="w-full" />
                <Input type="text" placeholder="Nombre para Enlace 2" value={name2} onChange={(e) => setName2(e.target.value)} className="w-full" />
                <div className="flex gap-2 mt-2">
                  <Button onClick={() => handleLinkSave(2, link2)} className="bg-green-800 text-white px-4 py-1 rounded transition">Guardar Enlace 2</Button>
                  <Button onClick={() => handleLinkDelete(2)} className="bg-red-700 text-white px-4 py-1 rounded transition">Eliminar Enlace 2</Button>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <Switch.Root checked={visible2} onCheckedChange={(v) => { setVisible2(!!v); setVisibility(2, !!v); }} className={`relative w-14 h-7 rounded-full ${visible2 ? "bg-green-900" : "bg-gray-300"} cursor-pointer transition-colors`}>
                    <Switch.Thumb className={`absolute top-1 left-1 w-5 h-5 bg-white rounded-full shadow-md transition-transform duration-300 ${visible2 ? "translate-x-7" : "translate-x-0"}`} />
                  </Switch.Root>
                  <span className="text-sm">Mostrar en Navbar</span>
                </div>
              </div>
              <div className="flex flex-col w-full md:w-1/2 gap-2">
                <label className="text-lg font-semibold text-green-950">🔗 Enlace 3:</label>
                <Input type="url" placeholder="https://ejemplo3.com" value={link3} onChange={(e) => setLink3(e.target.value)} className="w-full" />
                <Input type="text" placeholder="Nombre para Enlace 3" value={name3} onChange={(e) => setName3(e.target.value)} className="w-full" />
                <div className="flex gap-2 mt-2">
                  <Button onClick={() => handleLinkSave(3, link3)} className="bg-green-800 text-white px-4 py-1 rounded transition">Guardar Enlace 3</Button>
                  <Button onClick={() => handleLinkDelete(3)} className="bg-red-700 text-white px-4 py-1 rounded transition">Eliminar Enlace 3</Button>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <Switch.Root checked={visible3} onCheckedChange={(v) => { setVisible3(!!v); setVisibility(3, !!v); }} className={`relative w-14 h-7 rounded-full ${visible3 ? "bg-green-900" : "bg-gray-300"} cursor-pointer transition-colors`}>
                    <Switch.Thumb className={`absolute top-1 left-1 w-5 h-5 bg-white rounded-full shadow-md transition-transform duration-300 ${visible3 ? "translate-x-7" : "translate-x-0"}`} />
                  </Switch.Root>
                  <span className="text-sm">Mostrar en Navbar</span>
                </div>
              </div>
              <hr className="w-full my-4" />
              <div className="space-y-4 w-full md:w-1/2">
                <h3 className="text-lg font-semibold text-green-950">Tus Enlaces Rápidos:</h3>
                <p>Acá podes usar los link ingresados para un fácil acceso a las herramientas de tu negocio.</p>
                {link1 && (<Button onClick={() => window.open(link1, '_blank')} className="w-full bg-green-700 hover:bg-green-800 text-white px-4 py-2 rounded transition">{name1 || 'Enlace 1'}</Button>)}
                {!link1 && <p className="text-sm text-gray-500">Configura el Enlace 1 para habilitar el botón.</p>}
                {link2 && (<Button onClick={() => window.open(link2, '_blank')} className="w-full bg-green-700 hover:bg-green-800 text-white px-4 py-2 rounded transition">{name2 || 'Enlace 2'}</Button>)}
                {!link2 && <p className="text-sm text-gray-500">Configura el Enlace 2 para habilitar el botón.</p>}
                {link3 && (<Button onClick={() => window.open(link3, '_blank')} className="w-full bg-green-700 hover:bg-green-800 text-white px-4 py-2 rounded transition">{name3 || 'Enlace 3'}</Button>)}
                {!link3 && <p className="text-sm text-gray-500">Configura el Enlace 3 para habilitar el botón.</p>}
              </div>
            </div>
          </>
        )}

        {activeTab === 'integraciones' && (
          <>
            <div className="flex flex-col items-start gap-8 p-4">
              <div className="space-y-2">
                <h2 className="text-xl font-bold text-green-950">Integraciones y Módulos</h2>
                <p className="text-muted-foreground">Habilitá o deshabilitá módulos disponibles en tu empresa.</p>
              </div>
              <div className="flex flex-col gap-4 w-full md:w-1/2">
                <div className="flex items-center gap-4">
                  <Switch.Root
                    checked={mesasEnabled}
                    onCheckedChange={(v) => setMesasEnabled(!!v)}
                    className={`relative w-16 h-8 rounded-full ${mesasEnabled ? "bg-green-900" : "bg-gray-300"} cursor-pointer transition-colors`}
                  >
                    <Switch.Thumb
                      className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${mesasEnabled ? "translate-x-8" : "translate-x-0"}`}
                    />
                  </Switch.Root>
                  <h3 className="text-lg font-semibold text-green-950">Habilitar Módulo Mesas</h3>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={async () => {
                      if (!token || !empresaId) {
                        toast.error("Sesión no disponible");
                        return;
                      }
                      try {
                        const resGet = await fetch(`${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`, {
                          headers: { Authorization: `Bearer ${token}` },
                          cache: "no-store",
                        });
                        if (!resGet.ok) throw new Error("No se pudo leer configuración");
                        const data = await resGet.json();
                        const aclaraciones = {
                          ...(data.aclaraciones_legales ?? {}),
                          mesas_enabled: String(mesasEnabled),
                        };
                        const resPatch = await fetch(`${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`, {
                          method: "PATCH",
                          headers: {
                            "Content-Type": "application/json",
                            Authorization: `Bearer ${token}`,
                          },
                          body: JSON.stringify({ aclaraciones_legales: aclaraciones }),
                        });
                        if (!resPatch.ok) {
                          const err = await resPatch.json();
                          throw new Error(err.detail || "Error al guardar");
                        }
                        toast.success("Integración de Mesas actualizada");
                        eventBus.emit("empresa_actualizada");
                      } catch (e) {
                        const msg = e instanceof Error ? e.message : "Error desconocido";
                        toast.error("No se pudo guardar", { description: msg });
                      }
                    }}
                    className="bg-green-800 text-white"
                  >
                    Guardar cambios
                  </Button>
                  <Button
                    onClick={() => {
                      if (!mesasEnabled) {
                        toast.info("Activá Mesas para probar el módulo");
                        return;
                      }
                      nextRouter.push("/dashboard/mesas");
                    }}
                    className="bg-blue-700 text-white"
                  >
                    Probar Mesas
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">
                  Al habilitar Mesas, se mostrarán accesos en el menú y podrás administrar mesas y consumos.
                </p>
              </div>
            </div>
            {empresaId && <ConfiguracionForm empresaId={empresaId} sections={{ general: false, balanza: true, afip: false }} />}
          </>
        )}

      </div>
    </ProtectedRoute>
  );
}
