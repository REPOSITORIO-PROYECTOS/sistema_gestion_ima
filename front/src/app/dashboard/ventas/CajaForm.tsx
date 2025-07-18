"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";

interface CajaFormProps {
  cajaAbierta: boolean;
  onAbrirCaja: () => void;
  onCerrarCaja: () => void;
}

export default function CajaForm({
  cajaAbierta,
  onAbrirCaja,
  /* onCerrarCaja, */
}: CajaFormProps) {
  const token = useAuthStore((state) => state.token);

  const [nombre, setNombre] = useState("");
  const [montoInicial, setMontoInicial] = useState("");
  const [llave, setLlave] = useState("");

  const [fechaActual, setFechaActual] = useState("");
  const [horaActual, setHoraActual] = useState("");

  useEffect(() => {
    const updateDateTime = () => {
      const now = new Date();
      setFechaActual(
        now.toLocaleDateString("es-AR", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        })
      );
      setHoraActual(
        now.toLocaleTimeString("es-AR", {
          hour: "2-digit",
          minute: "2-digit",
        })
      );
    };

    updateDateTime();
    const interval = setInterval(updateDateTime, 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token) {
      alert("No se encontró el token.");
      return;
    }

    if (!nombre || !montoInicial || !llave) {
      alert("Por favor completá todos los campos.");
      return;
    }

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

      if (!res.ok) {
        alert(`⛔ Error: ${data.detail || "Llave incorrecta."}`);
        return;
      }

      console.log("🔓 Respuesta del backend:", data);

      alert("✅ Caja abierta correctamente.");
      onAbrirCaja();

      // (Opcional) Podés loguear esto en tu backend también:
      console.table({
        nombre,
        montoInicial,
        llave,
        fechaActual,
        horaActual,
      });

    } catch (err) {
      console.error("Error validando llave:", err);
      alert("Ocurrió un error al validar la llave.");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="grid gap-6 py-4">
        <div className="flex flex-row items-center justify-between gap-4">
          <Label className="text-right sm:text-lg">Nombre</Label>
          <Input
            placeholder="Pepe Prueba"
            className="w-full max-w-2/3"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
        </div>

        <div className="flex flex-row items-center justify-between gap-4">
          <Label className="text-right sm:text-lg">Monto Inicial</Label>
          <Input
            type="number"
            placeholder="Valor de la caja"
            className="w-full max-w-2/3"
            value={montoInicial}
            onChange={(e) => setMontoInicial(e.target.value)}
          />
        </div>

        <div className="flex flex-row items-center justify-between gap-4">
          <Label className="text-right sm:text-lg">Llave Maestra</Label>
          <Input
            type="password"
            placeholder="Clave del día"
            className="w-full max-w-2/3"
            value={llave}
            onChange={(e) => setLlave(e.target.value)}
          />
        </div>

        <div className="flex flex-row items-center justify-between gap-4">
          <Label className="text-right sm:text-lg">Fecha</Label>
          <Input
            value={fechaActual}
            disabled
            className="w-full max-w-2/3 text-green-950 font-semibold border border-white placeholder-white disabled:opacity-100 rounded-lg"
          />
        </div>

        <div className="flex flex-row items-center justify-between gap-4">
          <Label className="text-right sm:text-lg">Hora</Label>
          <Input
            value={horaActual}
            disabled
            className="w-full max-w-2/3 text-green-950 font-semibold border border-white placeholder-white disabled:opacity-100 rounded-lg"
          />
        </div>
      </div>

      <div className="flex justify-end mt-4">
        <Button type="submit" variant="success" className="w-full">
          {cajaAbierta ? "Cerrar Caja" : "Abrir Caja"}
        </Button>
      </div>
    </form>
  );
}