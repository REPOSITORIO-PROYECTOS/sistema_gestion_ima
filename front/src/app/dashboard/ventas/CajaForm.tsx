'use client'

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";
import { DialogClose } from "@/components/ui/dialog";
import { Loader2 } from "lucide-react";
import { useCajaStore } from "@/lib/cajaStore";

interface CajaFormProps {
  onAbrirCaja: () => void;
  onCerrarCaja: () => void;
}

export default function CajaForm({ onAbrirCaja, onCerrarCaja }: CajaFormProps) {
  
  const token = useAuthStore((state) => state.token);
  const usuario = useAuthStore((state) => state.usuario);

  const { cajaAbierta, setCajaAbierta, clearCaja } = useCajaStore();
  const [nombreUsuario, setNombreUsuario] = useState(usuario?.nombre_usuario || "");
  const [llave, setLlave] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [fechaActual, setFechaActual] = useState("");
  const [horaActual, setHoraActual] = useState("");
  
  /* Estados de la caja */
  // Monto inicial con el que se abre la caja
  const [saldoInicial, setSaldoInicial] = useState("");
  // Monto final al cerrar la caja
  const [saldoFinalDeclarado, setSaldoFinalDeclarado] = useState("");

  // Soluciona problema de input de nombre de usuario vacio 
  useEffect(() => {
    if (usuario?.nombre_usuario) {
      setNombreUsuario(usuario.nombre_usuario);
    }
  }, [usuario]);




  /* Formateos Numéricos */
  // Formatea el input numérico
  function formatearMoneda(valor: string): string {
    const limpio = valor.replace(/[^\d]/g, "");     // Todo menos dígitos
    if (!limpio) return "";
    const conPuntos = parseInt(limpio).toLocaleString("es-AR");
    return `$${conPuntos}`;
  }

  // Ayuda a limpiar el numero de input
  function limpiarMoneda(valor: string): number {
    if (!valor) return 0;
    const limpio = valor
      .replace(/\./g, "")    // Quitamos puntos (separador de miles)
      .replace(",", ".")     // Reemplazamos la coma decimal por punto
      .replace(/[^\d.]/g, ""); // Quitamos todo menos números y punto decimal
    return parseFloat(limpio) || 0;
  }



  // Abrir Caja
  const handleSubmit = async (e: React.FormEvent) => {
    
    e.preventDefault();

    // Validamos que no se manden datos vacíos
    if (!nombreUsuario.trim() || !saldoInicial.trim() || !llave.trim()) {
      toast.error("Por favor, completá todos los campos.");
      return;
    }

    if (parseFloat(saldoInicial) < 0) {
      toast.error("El monto inicial no puede ser negativo");
      return;
    }

    // Necesario para mejor UI numérica y convertir ese valor a float
    const saldoInicialLimpio = limpiarMoneda(saldoInicial);

    if (saldoInicialLimpio < 0) {
      toast.error("El monto inicial no puede ser negativo");
      return;
    }

    if (!token) return toast.error("No se encontró el token.");

    setIsLoading(true);

    try {
      // Paso 1: Validar la llave
      const res = await fetch("https://sistema-ima.sistemataup.online/api/auth/validar-llave", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ 
          llave,
          saldo_inicial: saldoInicialLimpio,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        return toast.error(`⛔ ${data.detail || "Llave incorrecta."}`);
      }

      // Paso 2: Abrir la caja una vez validados
      const abrirRes = await fetch("https://sistema-ima.sistemataup.online/api/caja/abrir", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          saldo_inicial: saldoInicialLimpio,
        }),
      });

      const abrirData = await abrirRes.json();
      if (!abrirRes.ok) {
        return toast.error(`⛔ ${abrirData.detail || "No se pudo abrir la caja."}`);
      }

      setCajaAbierta(true);
      toast.success(abrirData.message || "✅ Caja abierta correctamente.");
      onAbrirCaja();

    } catch (err) {
      console.error("Error abriendo caja:", err);
      toast.error("Ocurrió un error al abrir la caja.");
    } finally {
      setIsLoading(false);
      document.getElementById("close-caja-modal")?.click();
    }
  };

  // Cerrar caja
  const handleCerrarCaja = async () => {

    if (!nombreUsuario.trim() || !saldoFinalDeclarado.trim() || !llave.trim()) {
      toast.error("Por favor, completá todos los campos.");
      return;
    }

    if (parseFloat(saldoFinalDeclarado) < 0) {
      toast.error("El monto final no puede ser negativo");
      return;
    }

    if (!token) return toast.error("No se encontró el token.");
    setIsLoading(true);

    try {
      // Primero validamos la llave
      const validarRes = await fetch("https://sistema-ima.sistemataup.online/api/auth/validar-llave", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token,
        },
        body: JSON.stringify({ llave }),
      });

      const validarData = await validarRes.json();
      if (!validarRes.ok) {
        return toast.error(`⛔ ${validarData.detail || "Llave incorrecta."}`);
      }

      const saldoFinalLimpio = limpiarMoneda(saldoFinalDeclarado);

      // Si la llave es válida, cerramos la caja
      const cerrarRes = await fetch("https://sistema-ima.sistemataup.online/api/caja/cerrar", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          saldo_final_declarado: saldoFinalLimpio,
        }),
      });

      const cerrarData = await cerrarRes.json();
      if (!cerrarRes.ok) {
        return toast.error(`⛔ ${cerrarData.detail || "Error al cerrar la caja"}`);
      }

      toast.success(cerrarData.message || "✅ Caja cerrada correctamente.");
      clearCaja();
      onCerrarCaja();
      setNombreUsuario("");
      setSaldoFinalDeclarado("");
      setLlave("");


    } catch (error) {
      console.error("Error al cerrar caja:", error);
      toast.error("Ocurrió un error inesperado.");
    } finally {
      setIsLoading(false);
      document.getElementById("close-caja-modal")?.click();
    }
  };

  // Fecha y hora en vivo
  useState(() => {
    const now = new Date();
    setFechaActual(now.toLocaleDateString("es-AR"));
    setHoraActual(now.toLocaleTimeString("es-AR", {
      hour: "2-digit",
      minute: "2-digit",
    }));
  });

  return (
    <>
      <form onSubmit={handleSubmit}>

        <div className="grid gap-6 py-4">

          {/* Input Nombre */}
          <div className="flex items-center justify-between gap-4">
            <Label className="text-right text-md md:text-lg">Nombre</Label>
            <Input value={nombreUsuario} onChange={(e) => setNombreUsuario(e.target.value)} placeholder="Nombre de Usuario" className="w-full max-w-3/5" />
          </div>

          {/* Input Montos Iniciales y Finales */}
          <div className="flex items-center justify-between gap-4">
            <Label className="text-right text-md md:text-lg">
              {cajaAbierta ? "Monto de Cierre" : "Monto Inicial"}
            </Label>
            <Input
              type="text"
              value={cajaAbierta ? saldoFinalDeclarado : saldoInicial}
              onChange={(e) => {
                const formateado = formatearMoneda(e.target.value);
                return cajaAbierta
                  ? setSaldoFinalDeclarado(formateado)
                  : setSaldoInicial(formateado);
              }}
              placeholder="$0"
              className="w-full max-w-3/5"
            />
          </div>

          {/* Input Llave Maestra */}
          <div className="flex items-center justify-between gap-4">
            <Label className="text-right text-md md:text-lg">Llave Maestra</Label>
            <Input type="password" value={llave} onChange={(e) => setLlave(e.target.value)} placeholder="Llave del día" className="w-full max-w-3/5" />
          </div>

          {/* Fecha */}
          <div className="flex items-center justify-between gap-4">
            <Label className="text-right sm:text-lg">Fecha</Label>
            <Input value={fechaActual} disabled className="w-full max-w-3/5 text-green-950 font-semibold border border-white placeholder-white disabled:opacity-100 rounded-lg" />
          </div>

          {/* Hora */}
          <div className="flex items-center justify-between gap-4">
            <Label className="text-right sm:text-lg">Hora</Label>
            <Input value={horaActual} disabled className="w-full max-w-3/5 text-green-950 font-semibold border border-white placeholder-white disabled:opacity-100 rounded-lg" />
          </div>
        </div>

        {/* Botones de Abrir o Cerrar Caja */}
        <div className="flex justify-end mt-4 gap-2">
          {cajaAbierta ? (
            <Button type="button" variant="destructive" className="w-full" onClick={handleCerrarCaja} disabled={isLoading}>
              {isLoading && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
              Cerrar Caja
            </Button>
          ) : (
            <Button type="submit" variant="success" className="w-full" disabled={isLoading}>
              {isLoading && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
              Abrir Caja
            </Button>
          )}
        </div>
      </form>

      <DialogClose asChild>
        <button id="close-caja-modal" className="hidden" />
      </DialogClose>
    </>
  );
}