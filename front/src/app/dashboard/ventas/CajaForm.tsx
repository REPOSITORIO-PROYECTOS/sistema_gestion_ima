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
import {
  imprimirArqueoCaja,
  prepararVentanaImpresionCaja,
} from "@/lib/imprimir-arqueo";
import { API_CONFIG } from "@/lib/api-config";
import { useOfflineCache } from "@/hooks/useOfflineCache";
import { useEmpresaStore } from "@/lib/empresaStore";
import { intentarCerrarCaja } from "@/lib/offline/cierre-caja";



interface CajaFormProps {
  idEmpresa?: number;
  offlineHabilitado?: boolean;
  onAbrirCaja: () => void;
  onCerrarCaja: () => void;
}

type CajaResponse = {
  message?: string;
  detail?: string;
  data?: {
    id_sesion?: number;
  };
};

export default function CajaForm({
  idEmpresa,
  offlineHabilitado = false,
  onAbrirCaja,
  onCerrarCaja,
}: CajaFormProps) {
  
  const { cajaAbierta, idSesion, setCajaAbierta, clearCaja } = useCajaStore();
  const token = useAuthStore((state) => state.token);
  const usuario = useAuthStore((state) => state.usuario);
  const empresa = useEmpresaStore((state) => state.empresa);
  const { refrescarTrasAperturaCaja, refrescarTrasCierreCaja } = useOfflineCache({
    token,
    idEmpresa,
    enabled: offlineHabilitado,
  });
  
  const [nombreUsuario, setNombreUsuario] = useState(usuario?.nombre_usuario || "");
  // const [llave, setLlave] = useState(""); // ELIMINADO POR PEDIDO DEL USUARIO
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
    if (!nombreUsuario.trim() || !saldoInicial.trim()) {
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
    if (offlineHabilitado && typeof navigator !== "undefined" && navigator.onLine === false) {
      toast.error("Para abrir caja necesitás conexión con el servidor.");
      return;
    }

    setIsLoading(true);

    try {
      // Paso 2: Abrir la caja (Validación de llave eliminada por pedido)
      const abrirRes = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CAJA_ABRIR}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          saldo_inicial: saldoInicialLimpio,
        }),
      });

      const abrirData = (await abrirRes.json()) as CajaResponse;

      if (!abrirRes.ok) {
        return toast.error(`⛔ ${abrirData.detail || "No se pudo abrir la caja."}`);
      }

      const idSesion = abrirData.data?.id_sesion ?? null;
      if (offlineHabilitado && idSesion) {
        try {
          await refrescarTrasAperturaCaja(idSesion);
        } catch (cacheError) {
          console.error("Error refrescando caché offline:", cacheError);
          toast.warning("Caja abierta, pero no se pudo actualizar la caché offline.");
        }
      }

      setCajaAbierta(true, {
        idEmpresa,
        usarCacheDegradado: offlineHabilitado,
        idSesion,
      });
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
  const handleCerrarCaja = async (imprimirDespues: boolean) => {
    if (!nombreUsuario.trim()) {
      toast.error("Por favor, completá todos los campos.");
      return;
    }
    if (!token) return toast.error("No se encontró el token.");
    if (!idEmpresa) return toast.error("No se encontró la empresa.");

    const printWindow =
      imprimirDespues && offlineHabilitado === false
        ? prepararVentanaImpresionCaja()
        : null;
    if (imprimirDespues && offlineHabilitado === false && !printWindow) {
      toast.warning(
        "El navegador bloqueó la ventana de impresión. Se intentará descargar el PDF al finalizar.",
      );
    }

    setIsLoading(true);

    const saldoFinalLimpio = limpiarMoneda(saldoFinalDeclarado);
    const efectivo = limpiarMoneda(saldoFinalEfectivo);
    const transferencias = limpiarMoneda(saldoFinalTransferencias);
    const bancario = limpiarMoneda(saldoFinalBancario);

    try {
      const resultado = await intentarCerrarCaja({
        token,
        idEmpresa,
        offlineHabilitado,
        idSesionCaja: idSesion,
        saldos: {
          saldo_final_declarado: saldoFinalLimpio,
          saldo_final_efectivo: efectivo,
          saldo_final_transferencias: transferencias,
          saldo_final_bancario: bancario,
        },
        nombreUsuario: nombreUsuario.trim(),
        imprimir: imprimirDespues,
        empresaNombre: empresa?.nombre_negocio,
      });

      if (resultado.mode === "online") {
        toast.success(resultado.message || "✅ Caja cerrada correctamente.");

        if (imprimirDespues && resultado.id_sesion) {
          try {
            await imprimirArqueoCaja(resultado.id_sesion, token, printWindow);
          } catch (err) {
            console.error("Error al imprimir ticket de cierre:", err);
            if (err instanceof Error) {
              toast.error(`La caja se cerró, pero falló la impresión: ${err.message}`);
            }
          }
        }
      } else {
        toast.success(resultado.message);
        if (imprimirDespues) {
          toast.message("Se imprimió un resumen local del cierre.");
        }
      }

      if (offlineHabilitado) {
        try {
          await refrescarTrasCierreCaja();
        } catch (cacheError) {
          if (resultado.mode === "online") {
            console.error("Error refrescando caché offline al cerrar caja:", cacheError);
            toast.warning("Caja cerrada, pero no se pudo actualizar la caché offline.");
          }
        }
      }

      clearCaja({
        idEmpresa,
        usarCacheDegradado: offlineHabilitado,
      });
      onCerrarCaja();
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