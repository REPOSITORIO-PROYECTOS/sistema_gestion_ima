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
  /* onCerrarCaja, */
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

  const handleSubmit = (e: React.FormEvent) => {

    e.preventDefault();
    onAbrirCaja();

  }

  /* const handleSubmit = async (e: React.FormEvent) => {
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
  }; */


  return (
    <form /* onSubmit={handleSubmit} */>
      <div className="grid gap-6 py-4">
        <div className="flex flex-row items-center justify-between gap-4">
          <Label className="text-right sm:text-lg">Nombre</Label>
          <Input placeholder="Pepe Prueba" className="w-full max-w-2/3" />
        </div>

        <div className="flex flex-row items-center justify-between gap-4">
          <Label className="text-right sm:text-lg">Monto Inicial</Label>
          <Input placeholder="Valor de la caja al momento de la apertura" className="w-full max-w-2/3" />
        </div>

        <div className="flex flex-row items-center justify-between gap-4">
          <Label className="text-right sm:text-lg">Contraseña</Label>
          <Input placeholder="Clave Maestra?" className="w-full max-w-2/3" />
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
        <Button type="submit" variant="success" className="w-full" onClick={handleSubmit} >
          {cajaAbierta ? "Cerrar Caja" : "Abrir Caja"} 
        </Button>
      </div>
    </form>
  );
}