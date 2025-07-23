'use client'

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useState } from "react";
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
  const { cajaAbierta, setCajaAbierta, clearCaja } = useCajaStore();

  const [nombre, setNombre] = useState("");
  const [montoInicial, setMontoInicial] = useState("");
  const [llave, setLlave] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [fechaActual, setFechaActual] = useState("");
  const [horaActual, setHoraActual] = useState("");

  // Fecha y hora en vivo
  useState(() => {
    const now = new Date();
    setFechaActual(now.toLocaleDateString("es-AR"));
    setHoraActual(now.toLocaleTimeString("es-AR", {
      hour: "2-digit",
      minute: "2-digit",
    }));
  });


  // Abrir caja
  const handleSubmit = async (e: React.FormEvent) => {
    
    e.preventDefault();

    if (!token) return toast.error("No se encontró el token.");
    if (!nombre || !montoInicial || !llave)
      return toast.error("Por favor completá todos los campos.");

    setIsLoading(true);

    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/auth/validar-llave", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token,
        },
        body: JSON.stringify({ llave }),
      });

      const data = await res.json();
      if (!res.ok) return toast.error(`⛔ ${data.detail || "Llave incorrecta."}`);

      setCajaAbierta(true);
      toast.success(data.message || "✅ Caja abierta correctamente.");
      onAbrirCaja();

    } catch (err) {

      console.error("Error validando llave:", err);
      toast.error("Ocurrió un error al validar la llave.");

    } finally {

      setIsLoading(false);
      document.getElementById("close-caja-modal")?.click();
    }
  };

  // Cerrar caja
  const handleCerrarCaja = async () => {

    if (!token) return toast.error("No se encontró el token.");
    if (!nombre || !montoInicial) return toast.error("Por favor completá todos los campos.");

    setIsLoading(true);

    try {
      const cerrarRes = await fetch("https://sistema-ima.sistemataup.online/api/caja/cerrar", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          saldo_final_declarado: parseFloat(montoInicial),
        }),
      });

      const cerrarData = await cerrarRes.json();
      if (!cerrarRes.ok)
        return toast.error(`⛔ ${cerrarData.detail || "Error al cerrar la caja"}`);

      toast.success(cerrarData.message || "✅ Caja cerrada correctamente.");
      clearCaja();
      onCerrarCaja();
      setNombre("");
      setMontoInicial("");

    } catch (error) {

      console.error("Error al cerrar caja:", error);
      toast.error("Ocurrió un error inesperado.");
      
    } finally {

      setIsLoading(false);
      document.getElementById("close-caja-modal")?.click();
    }
  };


  return (
    <>
      <form onSubmit={handleSubmit}>
        <div className="grid gap-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <Label className="text-right text-md md:text-lg">Nombre</Label>
            <Input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nombre de Usuario" className="w-full max-w-3/5" />
          </div>

          <div className="flex items-center justify-between gap-4">
            <Label className="text-right text-md md:text-lg">{cajaAbierta ? "Monto de Cierre" : "Monto Inicial"}</Label>
            <Input type="number" value={montoInicial} onChange={(e) => setMontoInicial(e.target.value)} placeholder="Monto" className="w-full max-w-3/5" />
          </div>

          <div className="flex items-center justify-between gap-4">
            <Label className="text-right text-md md:text-lg">Llave Maestra</Label>
            <Input type="password" value={llave} onChange={(e) => setLlave(e.target.value)} placeholder="Llave del día" className="w-full max-w-3/5" />
          </div>

          <div className="flex items-center justify-between gap-4">
            <Label className="text-right sm:text-lg">Fecha</Label>
            <Input value={fechaActual} disabled className="w-full max-w-3/5 text-green-950 font-semibold border border-white placeholder-white disabled:opacity-100 rounded-lg" />
          </div>

          <div className="flex items-center justify-between gap-4">
            <Label className="text-right sm:text-lg">Hora</Label>
            <Input value={horaActual} disabled className="w-full max-w-3/5 text-green-950 font-semibold border border-white placeholder-white disabled:opacity-100 rounded-lg" />
          </div>
        </div>

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