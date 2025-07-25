'use client'

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";
import { DialogClose } from "@/components/ui/dialog";
import { Loader2 } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function EgresosForm() {
  
    const usuario = useAuthStore((state) => state.usuario);
    const token = useAuthStore((state) => state.token);

    const [nombreUsuario, setNombreUsuario] = useState(usuario?.nombre_usuario || "");
    const [isLoading, setIsLoading ] = useState(false);
    const [fechaActual, setFechaActual] = useState("");
    const [horaActual, setHoraActual] = useState("");

    const [metodoPago, setMetodoPago] = useState("efectivo");
    const [monto, setMonto] = useState("");
    const [concepto, setConcepto] = useState("");

    /* Soluciona problema de input de nombre de usuario vacio */
    useEffect(() => {
        if (usuario?.nombre_usuario) {
        setNombreUsuario(usuario.nombre_usuario);
        }
    }, [usuario]);

    // Fecha y hora en vivo
    useState(() => {
        const now = new Date();
        setFechaActual(now.toLocaleDateString("es-AR"));
        setHoraActual(now.toLocaleTimeString("es-AR", {
        hour: "2-digit",
        minute: "2-digit",
        }));
    });
   
    // POST Egreso de Dinero
    const handleSubmit = async () => {

        if (!concepto || !monto) {
            alert("Por favor completá todos los campos.");
            return;
        }

        const payload = {
            concepto,
            monto: parseFloat(monto),
            metodo_pago: metodoPago,
        };

        try {
            setIsLoading(true);

            const response = await fetch("https://sistema-ima.sistemataup.online/api/caja/egresos", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error("Error al enviar el egreso");
            }

            // Éxito
            alert("Egreso registrado correctamente.");
            toast.success("Egreso registrado correctamente!")
            document.getElementById("close-caja-modal")?.click(); // Cierra modal

            // Limpiar campos
            setConcepto("");
            setMonto("");

        } catch (error) {

            console.error("Error:", error);
            toast.error("Ocurrió un error al registrar el egreso.");

        } finally { setIsLoading(false); }
    };


    return (
    <>
        <form onSubmit={handleSubmit}>

            <div className="grid gap-6 py-4">

            {/* Input Nombre */}
            <div className="flex items-center justify-between gap-4">
                <Label className="text-right text-md md:text-lg">Nombre</Label>
                <Input value={nombreUsuario} onChange={(e) => setNombreUsuario(e.target.value)} placeholder="Nombre de Usuario" className="w-full max-w-3/5" />
            </div>

            {/* Input monto a solicitar */}
            <div className="flex items-center justify-between gap-4">
                <Label className="text-right text-md md:text-lg">
                    Monto solicitado: 
                </Label>
                <Input
                    type="number"
                    min="0"
                    value={monto}
                    onChange={(e) => setMonto(e.target.value)}
                    placeholder="Monto"
                    className="w-full max-w-3/5"
                />
            </div>

            {/* Método de Egreso */}
            <div className="flex flex-row items-center w-full justify-between">
                <Label className="text-md md:text-lg">Método de Pago</Label>
                <Select
                    value={metodoPago}
                    onValueChange={(value) => setMetodoPago(value)}
                >
                    <SelectTrigger className="w-full max-w-3/5 cursor-pointer text-black">
                    <SelectValue placeholder="Seleccionar método" />
                    </SelectTrigger>
                    <SelectContent>
                    <SelectItem value="efectivo">Efectivo</SelectItem>
                    <SelectItem value="transferencia">Transferencia</SelectItem>
                    </SelectContent>
                </Select>
            </div>


            {/* Concepto del egreso */}
            <div className="flex items-center justify-between gap-4">
                <Label className="text-right text-md md:text-lg">Concepto</Label>
                <Input
                    value={concepto}
                    onChange={(e) => setConcepto(e.target.value)}
                    placeholder="Motivo del egreso"
                    className="w-full max-w-3/5"
                />
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

            {/* Boton para enviar el egreso */}
            <div className="flex justify-end mt-4 gap-2">
                <Button type="button" variant="destructive" className="w-full" onClick={handleSubmit} disabled={isLoading}>
                {isLoading && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
                    Enviar egreso
                </Button>
            </div>

        </form>

        <DialogClose asChild>
            <button id="close-caja-modal" className="hidden" />
        </DialogClose>
    </>
    );
}