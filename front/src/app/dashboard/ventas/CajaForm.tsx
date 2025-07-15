import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";

interface CajaFormProps {
  cajaAbierta: boolean;
  onAbrirCaja: () => void;
  onCerrarCaja: () => void;
}

export default function CajaForm({
  cajaAbierta,
  onAbrirCaja,
  onCerrarCaja,
}: CajaFormProps) {

    // Funcion de Fecha y Hora
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

        const token = localStorage.getItem("admin_token");
        if (!token) {
            alert("No se encontró el token de administrador.");
            return;
        }

        if (cajaAbierta) {
            // Cerrar caja
            const payload = {
            id_sesion: 123,
            saldo_final_contado: 5500,
            usuario_cierre: "Pepe",
            };

            const res = await fetch("http://localhost:8000/admin/caja/cerrar", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Admin-Token": token,
            },
            body: JSON.stringify(payload),
            });

            if (!res.ok) {
            const error = await res.json();
            alert(`Error: ${error.detail}`);
            return;
            }

            const data = await res.json();
            console.log(data);
            alert("Caja cerrada correctamente.");
            onCerrarCaja();

        } else {
            // Abrir caja
            const payload = {
            usuario_apertura: "Pepe",
            monto_inicial: 5000,
            };

            const res = await fetch("http://localhost:8000/admin/caja/abrir", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Admin-Token": token,
            },
            body: JSON.stringify(payload),
            });

            if (!res.ok) {
            const error = await res.json();
            alert(`Error: ${error.detail}`);
            return;
            }

            const data = await res.json();
            console.log(data);
            alert("Caja abierta correctamente.");
            onAbrirCaja();
        }
    };


  return (
    <form onSubmit={handleSubmit}>
      <div className="grid gap-6 py-4">
        <div className="grid grid-cols-4 items-center gap-4">
          <Label className="text-right">Nombre</Label>
          <Input placeholder="Pepe Prueba" className="col-span-3" />
        </div>

        <div className="grid grid-cols-4 items-center gap-4">
          <Label className="text-right">Contraseña</Label>
          <Input placeholder="Clave Maestra?" className="col-span-3" />
        </div>

        <div className="grid grid-cols-4 items-center gap-4">
          <Label className="text-right">Fecha</Label>
          <Input
            value={fechaActual}
            disabled
            className="w-full text-green-950 font-semibold border border-white placeholder-white disabled:opacity-100 rounded-lg"
          />
        </div>

        <div className="grid grid-cols-4 items-center gap-4">
          <Label className="text-right">Hora</Label>
          <Input
            value={horaActual}
            disabled
            className="w-full text-green-950 font-semibold border border-white placeholder-white disabled:opacity-100 rounded-lg"
          />
        </div>
      </div>

      <div className="flex justify-end mt-4">
        <Button type="submit" variant="success">
          {cajaAbierta ? "Cerrar Caja" : "Abrir Caja"}
        </Button>
      </div>
    </form>
  );
}