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

const API_URL = "https://sistema-ima.sistemataup.online";

export default function GestionNegocio() {
  const token = useAuthStore((state) => state.token);
  const usuario = useAuthStore((state) => state.usuario);
  const empresaId = usuario?.id_empresa;

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
  } = useFacturacionStore();

  const [formatoComprobante, setFormatoComprobante] = useState<'ticket' | 'pdf' | string>('ticket');
  const [navbarColor, setNavbarColor] = useState("bg-sky-600");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!token) return;
    const fetchConfiguracionCompleta = async () => {
      try {
        const res = await fetch(`${API_URL}/api/configuracion/mi-empresa`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("No se pudo cargar la configuración.");
        
        const data = await res.json();
        setFormatoComprobante(data.formato_comprobante_predeterminado || 'ticket');
        setRecargoTransferencia(data.recargo_transferencia || 0);
        setRecargoBancario(data.recargo_bancario || 0);
        setNavbarColor(data.color_principal || 'bg-sky-600');

      } catch (error) {
        console.error("Error al obtener configuración:", error);
      }
    };
    fetchConfiguracionCompleta();
  }, [token, setRecargoBancario, setRecargoTransferencia]);

const handleFormatoChange = async (nuevoFormato: 'ticket' | 'pdf') => {
    if (!token) return;

    const valorAnterior = formatoComprobante;
    setFormatoComprobante(nuevoFormato); // Actualización optimista
    
    try {
      const res = await fetch(`${API_URL}/api/configuracion/mi-empresa`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          formato_comprobante_predeterminado: nuevoFormato
        }),
      });
      if (!res.ok) throw new Error("Error al guardar el formato.");
      
      toast.success("Formato de comprobante actualizado.");
      eventBus.emit("empresa_actualizada");

    } catch (error) {
      // La línea corregida:
      console.error("Error al guardar formato:", error);
      toast.error("Error al guardar.", { description: "Revertiendo cambio." });
      setFormatoComprobante(valorAnterior);
    }
  };


  const actualizarRecargoTransferencia = async () => {
    try {
      const res = await fetch(`${API_URL}/api/configuracion/mi-empresa/recargo/transferencia`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          porcentaje: recargoTransferencia,
          concepto: "Actualización recargo transferencia" 
        }),
      });
      if (!res.ok) throw new Error("Error en el PATCH");
      toast.success("Recargo por transferencia actualizado correctamente");
    } catch (error) {
      console.error("Error al actualizar recargo por transferencia:", error);
      toast.error("Error al actualizar el recargo por transferencia");
    }
  };

  const actualizarRecargoBancario = async () => {
    try {
      const res = await fetch(`${API_URL}/api/configuracion/mi-empresa/recargo/banco`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          porcentaje: recargoBancario,
          concepto: "Actualización recargo bancario"
        }),
      });
      if (!res.ok) throw new Error("Error en el PATCH");
      toast.success("Recargo por banco actualizado correctamente");
    } catch (error) {
      console.error("Error al actualizar recargo bancario:", error);
      toast.error("Error al actualizar el recargo por banco");
    }
  };

  const subirArchivo = async (file: File) => {
    if (!token) throw new Error("Token no disponible");
    const formData = new FormData();
    formData.append("archivo", file);
    const res = await fetch(`${API_URL}/api/configuracion/upload-logo`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "Error al subir el archivo");
    return data;
  };

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

      const res = await fetch(`${API_URL}/api/configuracion/mi-empresa`, {
        headers: { Authorization: `Bearer ${token}` },
      });
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

  const actualizarColorNavbar = async (nuevoColor: string) => {
    try {
      const res = await fetch(`${API_URL}/api/configuracion/mi-empresa/color`, {
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
      console.error("Error al actualizar el color de navbar:", error);
      toast.error("Error al actualizar el color de navbar");
    }
  };

  return (
    <ProtectedRoute allowedRoles={["Admin", "Soporte"]}>
      <div className="flex flex-col gap-6 p-2">

        {empresaId && <ConfiguracionForm empresaId={empresaId} />}

        <hr className="h-0.25 my-4" />

        <div className="space-y-2">
          <h2 className="text-xl font-bold text-green-950">Configuración de Impresión</h2>
          <p className="text-muted-foreground">Administra el formato predeterminado para los comprobantes de esta empresa.</p>
        </div>

        <div>
          <label className="text-sm font-medium text-gray-700 mb-1 block">Formato del Comprobante</label>
          <Select
            value={formatoComprobante}
            onValueChange={(value: 'ticket' | 'pdf') => handleFormatoChange(value)}
          >
            <SelectTrigger className="w-[220px] cursor-pointer">
              <SelectValue placeholder="Seleccionar formato" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ticket">Ticket (Impresora Térmica)</SelectItem>
              <SelectItem value="pdf">PDF (Hoja A4)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-4">
          <Switch.Root
            disabled={formatoComprobante !== "pdf"} // Lógica corregida a minúsculas
            checked={habilitarExtras}
            onCheckedChange={toggleExtras}
            className={`relative w-16 h-8 rounded-full ${
              habilitarExtras ? "bg-green-900" : "bg-gray-300"
            } cursor-pointer transition-colors ${
              formatoComprobante !== "pdf" ? "opacity-50 cursor-not-allowed" : "" // Lógica corregida a minúsculas
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

        <hr className="h-0.25 my-4" />

        <div className="space-y-2">
          <h2 className="text-xl font-bold text-green-950">Recargos asociados a métodos de pago.</h2>
          <p className="text-muted-foreground md:max-w-1/2">Desde acá podes asignar recargos a las opciones de transferencia o pago bancario.</p>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Switch.Root
              checked={recargoTransferenciaActivo}
              onCheckedChange={toggleRecargoTransferencia}
              className={`relative w-16 h-8 rounded-full ${recargoTransferenciaActivo ? "bg-green-900" : "bg-gray-300"} cursor-pointer transition-colors`}
            >
              <Switch.Thumb className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${recargoTransferenciaActivo ? "translate-x-8" : "translate-x-0"}`} />
            </Switch.Root>
            <h3 className="text-lg font-semibold text-green-950">Habilitar Recargo por Transferencia</h3>
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

        <hr className="p-0.25 bg-green-900 my-8"/>

        <div className="flex flex-col gap-2">
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Switch.Root
              checked={recargoBancarioActivo}
              onCheckedChange={toggleRecargoBancario}
              className={`relative w-16 h-8 rounded-full ${recargoBancarioActivo ? "bg-green-900" : "bg-gray-300"} cursor-pointer transition-colors`}
            >
              <Switch.Thumb className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow-md transition-transform duration-300 ${recargoBancarioActivo ? "translate-x-8" : "translate-x-0"}`} />
            </Switch.Root>
            <h3 className="text-lg font-semibold text-green-950">Habilitar Recargo por Bancario</h3>
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

        <hr className="h-0.25 my-4" />

        <div className="flex flex-col items-start gap-8 p-4">
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-green-950">Configuración de la Apariencia.</h2>
            <p className="text-muted-foreground">Administrá la apariencia de tu aplicación.</p>
          </div>
          <div className="flex flex-col sm:flex-row w-full md:w-1/2 items-start gap-8 mb-6">
            <label className="text-lg font-semibold text-green-950">🖌️ Personalizá el color de tu empresa:</label>
            <Select
              value={navbarColor}
              onValueChange={(val) => {
                setNavbarColor(val); 
                actualizarColorNavbar(val); 
              }}
            >
              <SelectTrigger className="w-full cursor-pointer"><SelectValue placeholder="Color del Navbar" /></SelectTrigger>
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