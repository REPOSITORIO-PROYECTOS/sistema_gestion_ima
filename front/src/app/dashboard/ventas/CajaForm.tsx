'use client'

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";
import { DialogClose } from "@/components/ui/dialog";
import { Loader2, PrinterIcon } from "lucide-react";
import { useCajaStore } from "@/lib/cajaStore";



interface CajaFormProps {
  onAbrirCaja: () => void;
  onCerrarCaja: () => void;
}

export default function CajaForm({ onAbrirCaja, onCerrarCaja }: CajaFormProps) {
  
  const { cajaAbierta, setCajaAbierta, clearCaja } = useCajaStore();
  const token = useAuthStore((state) => state.token);
  const usuario = useAuthStore((state) => state.usuario);
  
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

  // Discriminamos los 3 tipos de saldo para saldoFinalDeclarado
  const [saldoFinalTransferencias, setSaldoFinalTransferencias] = useState("");
  const [saldoFinalBancario, setSaldoFinalBancario] = useState("");
  const [saldoFinalEfectivo, setSaldoFinalEfectivo] = useState("");

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

  // Calcula el saldo final para el cierre de caja contando los 3 inputs
  useEffect(() => {
    const transf = limpiarMoneda(saldoFinalTransferencias);
    const bancario = limpiarMoneda(saldoFinalBancario);
    const efectivo = limpiarMoneda(saldoFinalEfectivo);

    const sumaTotal = transf + bancario + efectivo;
    setSaldoFinalDeclarado(formatearMoneda(sumaTotal.toString()));
  }, [saldoFinalTransferencias, saldoFinalBancario, saldoFinalEfectivo]);


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

const handleImprimirCierre = async (idSesionCerrada: number) => {
    if (!token) {
      toast.error("Token no encontrado. No se puede imprimir.");
      return;
    }
    
    toast.info("Generando ticket, por favor espere...");
    console.log(`[DEBUG] Iniciando impresión para sesión ID: ${idSesionCerrada}`);

    try {
      const url = `https://sistema-ima.sistemataup.online/api/caja/sesion/${idSesionCerrada}/ticket-cierre-detallado`;
      console.log(`[DEBUG] Llamando a la URL: ${url}`);

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });

      console.log(`[DEBUG] Respuesta recibida de la API. Estado: ${res.status}, Tipo de Contenido: ${res.headers.get('Content-Type')}`);

      if (!res.ok) {
        // Si el servidor envía un error, intentamos leerlo como JSON
        const errorData = await res.json();
        throw new Error(errorData.detail || `El servidor respondió con un error ${res.status}`);
      }
      
      // Convertimos la respuesta en un 'blob' (un objeto tipo archivo)
      const blob = await res.blob();
      console.log(`[DEBUG] Blob recibido. Tamaño: ${blob.size} bytes, Tipo: ${blob.type}`);

      // --- Verificaciones Clave ---
      if (blob.size === 0) {
        throw new Error("El servidor devolvió un archivo vacío.");
      }
      if (blob.type !== "application/pdf") {
        throw new Error(`El servidor devolvió un tipo de archivo incorrecto (${blob.type}), se esperaba un PDF.`);
      }

      // Creamos una URL temporal local para el archivo blob
      const fileURL = URL.createObjectURL(blob);
      
      // Abrimos la URL en una nueva pestaña. El navegador se encargará de mostrar el visor de PDF.
      const newWindow = window.open(fileURL, '_blank');
      
      if (!newWindow) {
        throw new Error("El navegador bloqueó la apertura de la nueva pestaña. Por favor, revisa la configuración de pop-ups.");
      }

      // Limpiamos la URL temporal después de un breve instante para darle tiempo al navegador de procesarla.
      setTimeout(() => URL.revokeObjectURL(fileURL), 100);

    } catch (err) {
      console.error("Error detallado al imprimir:", err); // Muestra el error completo en la consola
      if (err instanceof Error) {
        toast.error(`Error al imprimir: ${err.message}`);
      }
    }
};


  // Cerrar caja
  const handleCerrarCaja = async (imprimirDespues: boolean) => {
    if (!nombreUsuario.trim() || !llave.trim()) {
      toast.error("Por favor, completá todos los campos.");
      return;
    }
    if (!token) return toast.error("No se encontró el token.");
    
    setIsLoading(true);

    try {
      // Paso 1: Validar la llave (CON EL HEADER CORREGIDO)
      const validarRes = await fetch("https://sistema-ima.sistemataup.online/api/auth/validar-llave", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`, // <-- LA CORRECCIÓN CLAVE
        },
        body: JSON.stringify({ llave }),
      });
      if (!validarRes.ok) {
        const validarData = await validarRes.json();
        throw new Error(validarData.detail || "Llave incorrecta.");
      }

      // Paso 2: Si la llave es válida, cerramos la caja
      const saldoFinalLimpio = limpiarMoneda(saldoFinalDeclarado);
      const efectivo = limpiarMoneda(saldoFinalEfectivo);
      const transferencias = limpiarMoneda(saldoFinalTransferencias);
      const bancario = limpiarMoneda(saldoFinalBancario);
      
      const cerrarRes = await fetch("https://sistema-ima.sistemataup.online/api/caja/cerrar", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          saldo_final_declarado: saldoFinalLimpio,
          saldo_final_efectivo: efectivo,
          saldo_final_transferencias: transferencias,
          saldo_final_bancario: bancario,
        }),
      });

      const cerrarData = await cerrarRes.json();
      if (!cerrarRes.ok) {
        throw new Error(cerrarData.detail || "Error al cerrar la caja");
      }
      toast.success(cerrarData.message || "✅ Caja cerrada correctamente.");
      
      // LÓGICA CLAVE: Si se pidió imprimir, se llama a la función de impresión
    const idSesionCerrada = cerrarData.data?.id_sesion;
    if (imprimirDespues && idSesionCerrada) {
      await handleImprimirCierre(idSesionCerrada);
    }

      // Limpiamos todo
      clearCaja();
      onCerrarCaja();
      setLlave("");
      setSaldoFinalDeclarado("");
      setSaldoFinalEfectivo("");
      setSaldoFinalBancario("");
      setSaldoFinalTransferencias("");

    } catch (error) {
      if (error instanceof Error) toast.error(`⛔ ${error.message}`);
    } finally {
      setIsLoading(false);
      document.getElementById("close-caja-modal")?.click();
    }
  };

  // Fecha y hora en vivo
  useEffect(() => {
    const now = new Date();
    setFechaActual(now.toLocaleDateString("es-AR"));
    setHoraActual(now.toLocaleTimeString("es-AR", {
      hour: "2-digit",
      minute: "2-digit",
    }));
  }, []);


  return (
    <>
      <form>
        {/* ======================================================= */}
        {/* SECCIÓN PRINCIPAL DE INPUTS */}
        {/* ======================================================= */}
        <div className="grid gap-6 py-4">
          
          {/* --- Renderizado Condicional: Muestra "Monto Inicial" o los "Saldos Finales" --- */}
          {!cajaAbierta ? (
            // --- 1. VISTA PARA ABRIR CAJA (CUANDO LA CAJA ESTÁ CERRADA) ---
            <div className="flex items-center justify-between gap-4">
              <Label htmlFor="monto-inicial" className="text-right text-md md:text-lg">Monto Inicial</Label>
              <Input
                id="monto-inicial"
                type="text"
                value={saldoInicial}
                onChange={(e) => setSaldoInicial(formatearMoneda(e.target.value))}
                placeholder="$0"
                className="w-full max-w-3/5"
              />
            </div>
          ) : (
            // --- 2. VISTA PARA CERRAR CAJA (CUANDO LA CAJA ESTÁ ABIERTA) ---
            <>
              <Label className="text-left text-md md:text-xl font-semibold">Saldos Finales Declarados:</Label>
              
              <div className="flex items-center justify-between gap-4">
                <Label htmlFor="saldo-efectivo" className="text-right text-md md:text-lg">Efectivo</Label>
                <Input
                  id="saldo-efectivo"
                  type="text"
                  value={saldoFinalEfectivo}
                  onChange={(e) => setSaldoFinalEfectivo(formatearMoneda(e.target.value))}
                  placeholder="$0"
                  className="w-full max-w-3/5"
                />
              </div>

              <div className="flex items-center justify-between gap-4">
                <Label htmlFor="saldo-transferencias" className="text-right text-md md:text-lg">Transferencias</Label>
                <Input
                  id="saldo-transferencias"
                  type="text"
                  value={saldoFinalTransferencias}
                  onChange={(e) => setSaldoFinalTransferencias(formatearMoneda(e.target.value))}
                  placeholder="$0"
                  className="w-full max-w-3/5"
                />
              </div>

              <div className="flex items-center justify-between gap-4">
                <Label htmlFor="saldo-bancario" className="text-right text-md md:text-lg">POS</Label>
                <Input
                  id="saldo-bancario"
                  type="text"
                  value={saldoFinalBancario}
                  onChange={(e) => setSaldoFinalBancario(formatearMoneda(e.target.value))}
                  placeholder="$0"
                  className="w-full max-w-3/5"
                />
              </div>
            </>
          )}

          {/* Separador visual */}
          <span className="block w-full h-px bg-border my-2"></span>

          {/* --- CAMPOS COMUNES PARA ABRIR Y CERRAR --- */}
          <div className="flex items-center justify-between gap-4">
            <Label htmlFor="llave-maestra" className="text-right text-md md:text-lg">Llave Maestra</Label>
            <Input 
              id="llave-maestra"
              type="password" 
              value={llave} 
              onChange={(e) => setLlave(e.target.value)} 
              placeholder="Llave del día" 
              className="w-full max-w-3/5" 
            />
          </div>

          <div className="flex items-center justify-between gap-4">
            <Label className="text-right sm:text-lg">Fecha</Label>
            <Input 
              value={fechaActual} 
              disabled 
              className="w-full max-w-3/5 text-muted-foreground font-semibold" 
            />
          </div>

          <div className="flex items-center justify-between gap-4">
            <Label className="text-right sm:text-lg">Hora</Label>
            <Input 
              value={horaActual} 
              disabled 
              className="w-full max-w-3/5 text-muted-foreground font-semibold" 
            />
          </div>
        </div>

        {/* ======================================================= */}
        {/* SECCIÓN DE BOTONES DE ACCIÓN (CORREGIDA) */}
        {/* ======================================================= */}
        <div className="flex flex-col mt-4 gap-2">
          {cajaAbierta ? (
            // --- BOTONES PARA CERRAR CAJA ---
            <>
              <Button 
                type="button" 
                variant="destructive" 
                className="w-full" 
                onClick={() => handleCerrarCaja(true)} // Llama con 'true' para imprimir
                disabled={isLoading}
              >
                {isLoading ? <Loader2 className="animate-spin" /> : <PrinterIcon className="mr-2 h-4 w-4" />}
                Imprimir y Cerrar Caja
              </Button>
              
              <Button 
                type="button" 
                variant="outline" 
                className="w-full" 
                onClick={() => handleCerrarCaja(false)} // Llama con 'false' para NO imprimir
                disabled={isLoading}
              >
                {isLoading ? <Loader2 className="animate-spin" /> : "Sólo Cerrar Caja"}
              </Button>
            </>
          ) : (
            // --- BOTÓN PARA ABRIR CAJA ---
            <Button 
              type="button" 
              variant="success" 
              className="w-full" 
              onClick={handleSubmit} // Llama a la función de abrir caja
              disabled={isLoading}
            >
              {isLoading && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
              Abrir Caja
            </Button>
          )}
        </div>
      </form>

      <DialogClose asChild>
        <button id="close-caja-modal" className="hidden" aria-label="Cerrar modal"></button>
      </DialogClose>
    </>
  );
}