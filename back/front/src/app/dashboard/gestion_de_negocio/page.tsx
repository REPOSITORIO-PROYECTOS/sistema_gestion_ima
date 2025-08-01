'use client';

import { useFacturacionStore } from '@/lib/facturacionStore';
import * as Switch from '@radix-ui/react-switch';
import { useThemeStore } from '@/lib/themeStore'
import { Input } from "@/components/ui/input";
import Image from "next/image"
import { useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuthStore } from '@/lib/authStore';
import { toast } from 'sonner';

export default function GestionNegocio() {

  const token = useAuthStore((state) => state.token);
  const { setNavbarColor, setLogoUrl, navbarColor, logoUrl } = useThemeStore()
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

  const formatosDisponibles = ["PDF", "Ticket"];  // escalable a mas formatos..

  /* Negocio */
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

      alert("Recargo por transferencia actualizado correctamente");
    } catch (error) {
      console.error(error);
      alert("Error al actualizar el recargo por transferencia");
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

      alert("Recargo por banco actualizado correctamente");
    } catch (error) {
      console.error(error);
      alert("Error al actualizar el recargo por banco");
    }
  };


  /* UI */
  // Subir LOGO al Back para personalización
  const subirArchivo = async (file: File) => {
    const endpoint = "https://sistema-ima.sistemataup.online/api/configuracion/upload-logo";

    const formData = new FormData();
    formData.append("archivo", file);

    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`, // sin Content-Type
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

    try {
      const { message } = await subirArchivo(file);
      console.log(message);

      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result as string;
        setLogoUrl(dataUrl);
      };
      reader.readAsDataURL(file);

      toast.success("Logo subido correctamente.");
    } catch (error) {
      console.error(error);
      toast.error("Error al subir el logo");
    }
  };

  return (
    <div className="flex flex-col gap-6 p-2">

      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-3xl font-bold text-green-950">Gestión de Negocio</h2>
        <p className="text-muted-foreground">Administrá los usuarios de tu aplicación.</p>
      </div>

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
          className="w-1/3 mt-2"
        />

        <button
          onClick={actualizarRecargoTransferencia}
          disabled={!recargoTransferenciaActivo}
          className="bg-green-900 text-white px-4 py-1 rounded mt-2 w-1/3 disabled:opacity-50"
        >
          Guardar recargo transferencia
        </button>
      </div>

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
          className="w-1/3 mt-2"
        />

        <button
          onClick={actualizarRecargoBancario}
          disabled={!recargoBancarioActivo}
          className="bg-green-900 text-white px-4 py-1 rounded mt-2 w-1/3 disabled:opacity-50"
        >
          Guardar recargo bancario
        </button>
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
        <div className="flex flex-col gap-2">
          <label className="block text-md font-semibold mb-1">Color de la barra de Navegación</label>
          
          <Select value={navbarColor} onValueChange={setNavbarColor}>
            <SelectTrigger className="w-2/3 cursor-pointer">
              <SelectValue placeholder="Selecciona un color" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="bg-green-800">Verde Oscuro</SelectItem>
              <SelectItem value="bg-blue-800">Azul Oscuro</SelectItem>
              <SelectItem value="bg-red-800">Rojo Oscuro</SelectItem>
              <SelectItem value="bg-gray-800">Gris Oscuro</SelectItem>
            </SelectContent>
          </Select>
          
        </div>

        {/* LOGO */}
        <div className="flex flex-col items-start gap-4 mb-6">
          <label className="text-md font-semibold mb-1">Logo actual:</label>
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Image src={logoUrl} alt="Logo actual" width={60} height={60} />
            <Input
              type="file"
              accept=".png,.jpg,.jpeg,.webp"
              onChange={handleFileChange}
              className="max-w-sm"
            />
          </div>
        </div>
    </div>

    </div>
  );
}