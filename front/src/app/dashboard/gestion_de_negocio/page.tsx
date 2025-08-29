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
          fetch("https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa/recargo/transferencia", {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch("https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa/recargo/banco", {
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

  // PATCH Recargos transferencia
  const actualizarRecargoTransferencia = async () => {
    try {
      const res = await fetch(
        "https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa/recargo/transferencia",
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
        "https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa/recargo/banco",
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

    const res = await fetch("https://sistema-ima.sistemataup.online/api/configuracion/upload-logo", {
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
      const res = await fetch("https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa",
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

  // Cargamos los enlaces al iniciar el componente
  useEffect(() => {
    if (!token) return;

    const fetchLinks = async () => {
      try {
        const [resLink1, resLink2, resLink3] = await Promise.all([
          fetch("https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa/link/1", {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch("https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa/link/2", {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch("https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa/link/3", {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        const dataLink1 = await resLink1.json();
        const dataLink2 = await resLink2.json();
        const dataLink3 = await resLink3.json();

        setLink1(dataLink1.url || '');
        setLink2(dataLink2.url || '');
        setLink3(dataLink3.url || '');

      } catch (error) {
        console.error("Error al obtener los enlaces:", error);
        toast.error("Error al obtener los enlaces personalizados.");
      }
    };

    fetchLinks();
  }, [token]);

  // Handler para enviar un nuevo link (POST)
  const handleLinkSubmit = async (linkNumber: number, url: string) => {
    if (!token) {
      toast.error("No hay token de sesión, vuelva a iniciar sesión");
      return;
    }
    if (!url.trim()) {
      toast.error("El enlace no puede estar vacío.");
      return;
    }

    try {
      const res = await fetch(`https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa/link/${linkNumber}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ url }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.message || "Error al agregar el enlace");
      }

      toast.success(`Enlace ${linkNumber} agregado correctamente.`);
      // Opcional: Recargar los links para asegurar la consistencia si el backend no devuelve el valor actualizado
      // fetchLinks(); 

    } catch (error) {
      console.error(`Error al agregar el enlace ${linkNumber}:`, error);
      toast.error(`Error al agregar el enlace ${linkNumber}`);
    }
  };

  // Handler para modificar un link existente (PATCH)
  const handleLinkEdit = async (linkNumber: number, url: string) => {
    if (!token) {
      toast.error("No hay token de sesión, vuelva a iniciar sesión");
      return;
    }
    if (!url.trim()) {
      toast.error("El enlace no puede estar vacío.");
      return;
    }

    try {
      const res = await fetch(`https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa/link/${linkNumber}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ url }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.message || "Error al modificar el enlace");
      }

      toast.success(`Enlace ${linkNumber} modificado correctamente.`);
      // Opcional: Recargar los links para asegurar la consistencia si el backend no devuelve el valor actualizado
      // fetchLinks(); 

    } catch (error) {
      console.error(`Error al modificar el enlace ${linkNumber}:`, error);
      toast.error(`Error al modificar el enlace ${linkNumber}`);
    }
  };


  return (
    <ProtectedRoute allowedRoles={["Admin", "Soporte"]}>
      <div className="flex flex-col gap-6 p-2">

        {/* Gestión de datos de empresa */}
        {empresaId && (
          <ConfiguracionForm empresaId={empresaId} />
        )}

        <hr className="h-0.25 my-4" />  {/* --------------------------------------------------------------- */}

        {/* Header para método de pago y recargos*/}
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-green-950">Configuración sobre métodos de pago</h2>
          <p className="text-muted-foreground">Administrá el tipo de ticket para imprimir.</p>
        </div>

        {/* Toggle de Facturación en Caja */}
        <div>
          <label className="text-sm font-medium text-gray-700 mb-1 block">Formato del Comprobante</label>
          <Select
            value={formatoComprobante}
            onValueChange={setFormatoComprobante}
          >
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

        {/* Toggle de Facturación en Caja */}
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <Switch.Root
            disabled={formatoComprobante !== "PDF"}
            checked={habilitarExtras}
            onCheckedChange={toggleExtras}
            className={`relative w-16 h-8 rounded-full ${
              habilitarExtras ? "bg-green-900" : "bg-gray-300"
            } cursor-pointer transition-colors ${
              formatoComprobante !== "PDF" ? "opacity-50 cursor-not-allowed" : ""
            }`}
          >
            <Switch.Thumb
              className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${
                habilitarExtras ? "translate-x-8" : "translate-x-0"
              }`}
            />
          </Switch.Root>

          <h3 className="text-lg font-semibold text-green-950">
            Habilitar Remito / Presupuesto
          </h3>
        </div>

        <hr className="h-0.25 my-4" />  {/* --------------------------------------------------------------- */}

        {/* Header para método de pago y recargos*/}
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-green-950">Recargos asociados a métodos de pago.</h2>
          <p className="text-muted-foreground md:max-w-1/2">Desde acá podes asignar recargos a las opciones de transferencia o pago bancario. El valor que ves es el recargo actual, podes reemplazarlo y setear uno nuevo.</p>
        </div>

        {/* Recargo por Transferencia */}
        <div className="flex flex-col gap-2">
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Switch.Root
              checked={recargoTransferenciaActivo}
              onCheckedChange={toggleRecargoTransferencia}
              className={`relative w-16 h-8 rounded-full ${
                recargoTransferenciaActivo ? "bg-green-900" : "bg-gray-300"
              } cursor-pointer transition-colors`}
            >
              <Switch.Thumb
                className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${
                  recargoTransferenciaActivo ? "translate-x-8" : "translate-x-0"
                }`}
              />
            </Switch.Root>

            <h3 className="text-lg font-semibold text-green-950">
              Habilitar Recargo por Transferencia
            </h3>
          </div>

          <Input
            type="number"
            placeholder="Ej: 10"
            disabled={!recargoTransferenciaActivo}
            value={recargoTransferencia}
            onChange={(e) => {
              const rawValue = e.target.value;
              if (rawValue === "") return setRecargoTransferencia(0);
              const val = Number(rawValue);
              if (val >= 0 && val <= 100) setRecargoTransferencia(val);
            }}
            className="w-full md:w-1/3 mt-2"
          />

          <Button
            onClick={actualizarRecargoTransferencia}
            disabled={!recargoTransferenciaActivo}
            className="w-full md:w-1/3 bg-green-900 text-white px-4 py-1 rounded mt-2 disabled:opacity-50 transition"
          >
            Guardar recargo transferencia
          </Button>
        </div>

        <hr className="h-0.25 my-4" />  {/* --------------------------------------------------------------- */}

        {/* Recargo por Bancario */}
        <div className="flex flex-col gap-2">
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Switch.Root
              checked={recargoBancarioActivo}
              onCheckedChange={toggleRecargoBancario}
              className={`relative w-16 h-8 rounded-full ${
                recargoBancarioActivo ? "bg-green-900" : "bg-gray-300"
              } cursor-pointer transition-colors`}
            >
              <Switch.Thumb
                className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${
                  recargoBancarioActivo ? "translate-x-8" : "translate-x-0"
                }`}
              />
            </Switch.Root>

            <h3 className="text-lg font-semibold text-green-950">
              Habilitar Recargo por Bancario
            </h3>
          </div>

          <Input
            type="number"
            placeholder="Ej: 10"
            disabled={!recargoBancarioActivo}
            value={recargoBancario}
            onChange={(e) => {
              const rawValue = e.target.value;
              if (rawValue === "") return setRecargoBancario(0);
              const val = Number(rawValue);
              if (val >= 0 && val <= 100) setRecargoBancario(val);
            }}
            className="w-full md:w-1/3 mt-2"
          />

          <Button
            onClick={actualizarRecargoBancario}
            disabled={!recargoBancarioActivo}
            className="w-full md:w-1/3 bg-green-900 text-white px-4 py-1 rounded mt-2 disabled:opacity-50 transition"
          >
            Guardar recargo bancario
          </Button>
        </div>

        <hr className="h-0.25 my-4" />  {/* --------------------------------------------------------------- */}

        {/* Sección de Enlaces Personalizados */}
        <div className="flex flex-col items-start gap-8 p-4">
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-green-950">Enlaces Personalizados.</h2>
            <p className="text-muted-foreground">Configurá enlaces externos para acceso rápido.</p>
          </div>

          {/* Enlace 1 */}
          <div className="flex flex-col w-full md:w-1/2 gap-2">
            <label className="text-lg font-semibold text-green-950">🔗 Enlace 1:</label>
            <Input
              type="url"
              placeholder="https://ejemplo.com"
              value={link1}
              onChange={(e) => setLink1(e.target.value)}
              className="w-full"
            />
            <div className="flex gap-2 mt-2">
              <Button onClick={() => handleLinkSubmit(1, link1)} className="bg-green-800 text-white px-4 py-1 rounded transition">
                Agregar Enlace 1
              </Button>
              <Button onClick={() => handleLinkEdit(1, link1)} className="bg-yellow-600 text-white px-4 py-1 rounded transition">
                Editar Enlace 1
              </Button>
            </div>
          </div>

          {/* Enlace 2 */}
          <div className="flex flex-col w-full md:w-1/2 gap-2">
            <label className="text-lg font-semibold text-green-950">🔗 Enlace 2:</label>
            <Input
              type="url"
              placeholder="https://ejemplo2.com"
              value={link2}
              onChange={(e) => setLink2(e.target.value)}
              className="w-full"
            />
            <div className="flex gap-2 mt-2">
              <Button onClick={() => handleLinkSubmit(2, link2)} className="bg-green-800 text-white px-4 py-1 rounded transition">
                Agregar Enlace 2
              </Button>
              <Button onClick={() => handleLinkEdit(2, link2)} className="bg-yellow-600 text-white px-4 py-1 rounded transition">
                Editar Enlace 2
              </Button>
            </div>
          </div>

          {/* Enlace 3 */}
          <div className="flex flex-col w-full md:w-1/2 gap-2">
            <label className="text-lg font-semibold text-green-950">🔗 Enlace 3:</label>
            <Input
              type="url"
              placeholder="https://ejemplo3.com"
              value={link3}
              onChange={(e) => setLink3(e.target.value)}
              className="w-full"
            />
            <div className="flex gap-2 mt-2">
              <Button onClick={() => handleLinkSubmit(3, link3)} className="bg-green-800 text-white px-4 py-1 rounded transition">
                Agregar Enlace 3
              </Button>
              <Button onClick={() => handleLinkEdit(3, link3)} className="bg-yellow-600 text-white px-4 py-1 rounded transition">
                Editar Enlace 3
              </Button>
            </div>
          </div>

          <hr className="w-full my-4" />

          {/* Botones de Redirección */}
          <div className="space-y-4 w-full md:w-1/2">
            <h3 className="text-lg font-semibold text-green-950">Tus Enlaces Rápidos:</h3>
            <p>Acá podes usar los link ingresados para un fácil acceso a las herramientas de tu negocio.</p>
            {link1 && (
              <Button 
                onClick={() => window.open(link1, '_blank')} 
                className="w-full bg-green-700 hover:bg-green-800 text-white px-4 py-2 rounded transition"
              >
                Ir a Enlace 1
              </Button>
            )}
            {!link1 && <p className="text-sm text-gray-500">Configura el Enlace 1 para habilitar el botón.</p>}

            {link2 && (
              <Button 
                onClick={() => window.open(link2, '_blank')} 
                className="w-full bg-green-700 hover:bg-green-800 text-white px-4 py-2 rounded transition"
              >
                Ir a Enlace 2
              </Button>
            )}
            {!link2 && <p className="text-sm text-gray-500">Configura el Enlace 2 para habilitar el botón.</p>}

            {link3 && (
              <Button 
                onClick={() => window.open(link3, '_blank')} 
                className="w-full bg-green-700 hover:bg-green-800 text-white px-4 py-2 rounded transition"
              >
                Ir a Enlace 3
              </Button>
            )}
            {!link3 && <p className="text-sm text-gray-500">Configura el Enlace 3 para habilitar el botón.</p>}
          </div>
        </div>

        <hr className="h-0.25 my-4" />  {/* --------------------------------------------------------------- */}

        {/* Configuración de Negocios - UI */}
        <div className="flex flex-col items-start gap-8 p-4">

          {/* Header para personalización */}
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-green-950">Configuración de la Apariencia.</h2>
            <p className="text-muted-foreground">Administrá la apariencia de tu aplicación.</p>
          </div>

          {/* Color del Nav */}
          <div className="flex flex-col sm:flex-row w-full md:w-1/2 items-start gap-8 mb-6">
            <label className="text-lg font-semibold text-green-950">🖌️ Personalizá el color de tu empresa:</label>
            <Select
              value={navbarColor}
              onValueChange={(val) => {
                setNavbarColor(val); 
                actualizarColorNavbar(val); 
              }}
            >
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

          {/* LOGO */}
          <div className="flex flex-col sm:flex-row w-full md:w-1/2 items-start gap-8 mb-6">
            <label className="text-lg font-semibold text-green-950">🎨 Cambiar logo de empresa:</label>
            <Input
              type="file"
              accept=".png,.jpg,.jpeg,.webp"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="max-w-sm"
            />
          </div>

        </div>

      </div>
    </ProtectedRoute>
  );
}