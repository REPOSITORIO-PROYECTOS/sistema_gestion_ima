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
import { API_CONFIG } from "@/lib/api-config";

export default function EgresosForm() {
  
    const usuario = useAuthStore((state) => state.usuario);
    const token = useAuthStore((state) => state.token);

    const [nombreUsuario, setNombreUsuario] = useState(usuario?.nombre_usuario || "");
    const [isLoading, setIsLoading ] = useState(false);
    const [fechaActual, setFechaActual] = useState("");
    const [horaActual, setHoraActual] = useState("");

    const [tipoMovimiento, setTipoMovimiento] = useState<"egreso" | "ingreso">("egreso");
    const [metodoPago, setMetodoPago] = useState("efectivo");
    const [monto, setMonto] = useState("");
    const [concepto, setConcepto] = useState("");

    const esEgreso = tipoMovimiento === "egreso";

    // Ayuda a limpiar el numero de input
    function limpiarMoneda(valor: string): number {
        if (!valor) return 0;
        const limpio = valor
        .replace(/\./g, "")    // Quitamos puntos (separador de miles)
        .replace(",", ".")     // Reemplazamos la coma decimal por punto
        .replace(/[^\d.]/g, ""); // Quitamos todo menos números y punto decimal
        return parseFloat(limpio) || 0;
    }

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
   
    // POST Movimiento de Dinero (ingreso o egreso)
    const handleSubmit = async () => {

        if (!concepto || !monto) {
            toast.error("Por favor completá todos los campos.");
            return;
        }

        const payload = {
            concepto,
            monto: limpiarMoneda(monto),
            metodo_pago: metodoPago,
        };

        const endpoint = esEgreso
            ? API_CONFIG.ENDPOINTS.CAJA_EGRESOS
            : API_CONFIG.ENDPOINTS.CAJA_INGRESOS;
        const etiquetaTipo = esEgreso ? "Egreso" : "Ingreso";

        try {
            setIsLoading(true);

            const response = await fetch(`${API_CONFIG.BASE_URL}${endpoint}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error("Error al registrar el movimiento");
            }

            // Éxito
            toast.success(`${etiquetaTipo} de dinero registrado correctamente!`)

            // Cierra Modal
            document.getElementById("close-caja-modal")?.click();

            // Limpiar campos
            setConcepto("");
            setMonto("");

        } catch (error) {

            console.error("Error:", error);
            toast.error("Ocurrió un error al registrar el movimiento.");

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

                    {/* Tipo de movimiento */}
                    <div className="flex flex-row items-center w-full justify-between">
                        <Label className="text-md md:text-lg">Tipo de Movimiento</Label>
                        <Select
                            value={tipoMovimiento}
                            onValueChange={(value) => setTipoMovimiento(value as "egreso" | "ingreso")}
                        >
                            <SelectTrigger className="w-full max-w-3/5 cursor-pointer text-black">
                            <SelectValue placeholder="Seleccionar tipo" />
                            </SelectTrigger>
                            <SelectContent>
                            <SelectItem value="egreso">Egreso (salida de dinero)</SelectItem>
                            <SelectItem value="ingreso">Ingreso (entrada de dinero)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {/* Input monto a solicitar */}
                    <div className="flex items-center justify-between gap-4">
                        <Label className="text-right text-md md:text-lg">
                            Monto solicitado: 
                        </Label>
                        <Input
                            type="text"
                            inputMode="numeric"
                            value={monto}
                            onChange={(e) => {
                                const valor = e.target.value;

                                // Limpiamos cualquier carácter no numérico válido
                                const limpio = valor
                                .replace(/\D/g, "")     // Quitar todo lo que no sea número
                                .replace(/^0+/, "");    // Evitar ceros al inicio

                                // Formateamos como moneda argentina (con puntos y $)
                                const numero = parseFloat(limpio) / 100;
                                const formateado = isNaN(numero)
                                ? ""
                                : numero.toLocaleString("es-AR", {
                                    style: "currency",
                                    currency: "ARS",
                                    minimumFractionDigits: 2,
                                    });

                                setMonto(formateado);
                            }}
                            placeholder="$ 0,00"
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

                    {/* Detalle del movimiento */}
                    <div className="flex items-center justify-between gap-4">
                        <Label className="text-right text-md md:text-lg">Concepto</Label>
                        <Input
                            value={concepto}
                            onChange={(e) => setConcepto(e.target.value)}
                            placeholder={esEgreso ? "Detalle del egreso" : "Detalle del ingreso"}
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

                    {/* Boton para enviar el movimiento */}
                    
                    <div className="flex justify-end mt-4 gap-2">
                    <Button type="button" variant={esEgreso ? "destructive" : "default"} className="w-full" onClick={handleSubmit} disabled={isLoading} aria-label="Registrar movimiento">
                    {isLoading && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
                        {esEgreso ? "Registrar egreso" : "Registrar ingreso"}
                    </Button>
                </div>

            </form>

            <DialogClose asChild>
                <button id="close-caja-modal" className="hidden" aria-label="Close modal" title="Close modal" />
            </DialogClose>
        </>
    );
}