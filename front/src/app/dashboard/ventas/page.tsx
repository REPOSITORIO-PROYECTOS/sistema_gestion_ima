"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import FormVentas from "./FormVentas";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuthStore } from "@/lib/authStore";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import CajaForm from "./CajaForm";
import { useCajaStore } from "@/lib/cajaStore";
import EgresoForm from "./EgresoForm";

function DashboardVenta() {

  /* Estados de la Caja de Ventas */
   const verificarEstadoCaja = useCajaStore(state => state.verificarEstadoCaja);
  const token = useAuthStore((state) => state.token);
  const [productos, setProductos] = useState<{
    tipo: string;
    cantidad: number;
    precioTotal: number;
    descuentoAplicado?: boolean;
    porcentajeDescuento?: number;
  }[]>([]);
  const [fechaActual, setFechaActual] = useState("");
  const [horaActual, setHoraActual] = useState("");  
  const { cajaAbierta } = useCajaStore();
  const role = useAuthStore((state) => state.role);   

  // Hook para calcular fecha y hora en vivo
  useEffect(() => {
    const updateDateTime = () => {
      
      const now = new Date();

      setFechaActual(
        now.toLocaleDateString("es-AR", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          timeZone: "America/Argentina/Buenos_Aires",
        })
      );

      setHoraActual(
        now.toLocaleTimeString("es-AR", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
          timeZone: "America/Argentina/Buenos_Aires",
        })
      );
    };

    updateDateTime();

    const interval = setInterval(updateDateTime, 60 * 1000); // cada 1 minuto

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (token) {
      console.log("Token detectado, verificando estado de la caja...");
      verificarEstadoCaja(token);
    }
  }, [token, verificarEstadoCaja]);
  // Mapeamos el rol para mostrarlo legible
  const mostrarRol = () => {
    if (role?.nombre === "Admin") return "Administrador";
    if (role?.nombre === "Cajero") return "Cajero";
    if (role?.nombre === "Gerente") return "Gerente";
    if (role?.nombre === "Cliente") return "Cliente";
    return "Rol no identificado";
  };

  const totalVenta = productos.reduce((acc, prod) => acc + prod.precioTotal, 0);

  const handleAgregarProducto = (producto: { tipo: string; cantidad: number; precioTotal: number }) => {
    setProductos((prev) => [...prev, producto]);
  };

  const handleEliminarProducto = (index: number) => {
    setProductos((prev) => prev.filter((_, i) => i !== index));
  };

  const limpiarResumen = () => {
    setProductos([]);
  };


  return (
    <ProtectedRoute allowedRoles={["Admin", "Cajero"]}>
      <div className="flex flex-col gap-4">

        {/* Header de Informacion */}
        <div className="flex flex-wrap justify-between items-center p-4 gap-4 bg-neutral-800/90 rounded-xl px-6">
          {/* Fecha y Hora */}
          <Input
            value={`${fechaActual}     -     ${horaActual}`}
            disabled
            className="w-full sm:w-[48%] lg:w-[23%] text-white font-semibold border border-white bg-transparent placeholder-white disabled:opacity-100 rounded-lg text-start"
          />
          {/* Muestra Rol */}
          <Input
            value={mostrarRol()}
            disabled
            className="w-full sm:w-[48%] lg:w-[23%] text-white font-semibold border border-white bg-transparent placeholder-white disabled:opacity-100 rounded-lg"
          />
          
          {/* Modal para egresos de dinero en efectivo */}
          <Dialog>
              <DialogTrigger asChild className="w-full sm:w-[48%] lg:w-[23%]">
                <Button type="button" variant="success" disabled={!cajaAbierta}>
                  Egresos de Dinero
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Egresos de Dinero en Efectivo</DialogTitle>
                  <DialogDescription>Si desea retirar dinero en efectivo de la caja, complete los datos</DialogDescription>
                </DialogHeader>

                {/* Modal de Egreso de Dinero */}
                <EgresoForm />
              </DialogContent>
          </Dialog>

          {/* Boton Abrir / Cerrar Caja */}
          <Dialog>
              <DialogTrigger asChild className="w-full sm:w-[48%] lg:w-[23%]">
                  <Button type="submit" variant="success">
                    {cajaAbierta ? "Cerrar Caja" : "Abrir Caja"}
                  </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>Apertura / Cierre de Caja</DialogTitle>
                  <DialogDescription>Ingrese los datos solicitados para abrir la caja</DialogDescription>
                </DialogHeader>

                {/* Modal de Apertura / Cierre de caja */}
                <CajaForm
                  onAbrirCaja={() => {}}
                  onCerrarCaja={() => {}}
                />
              </DialogContent>
          </Dialog>
        </div>

        {/* Bloque principal: Resumen + Formulario */}
        <div className="flex flex-col-reverse md:flex-row justify-between gap-4">

          {/* Panel izquierdo: Resumen */}
          <div className="flex flex-col items-start w-full lg:w-1/2 md:max-w-2/3 bg-gray-100 rounded-xl shadow-md">
            <div className="w-full flex flex-row justify-between items-center p-6 bg-green-700 rounded-t-xl">
              <h4 className="text-xl font-semibold text-white">Resumen del Pedido</h4>
              <p className="text-2xl font-semibold text-white">Total: ${totalVenta}</p>
            </div>

            <ul className="flex flex-col items-center w-full p-6 gap-5 overflow-y-auto">
              {productos.map((prod, index) => (
                <li
                  key={index}
                  className="flex flex-col md:flex-row w-full justify-between items-start md:items-center px-8 py-6 bg-emerald-100 rounded-lg text-green-950 font-semibold border-3 border-green-800 text-xl shadow-lg"
                >
                  <div className="flex flex-col">
                    <span>{prod.tipo} - x{prod.cantidad} U. - ${prod.precioTotal}</span>

                    {prod.descuentoAplicado && (
                      <span className="text-green-800 text-sm font-normal italic">
                        Descuento aplicado: {prod.porcentajeDescuento}% OFF
                      </span>
                    )}
                  </div>

                  <Button variant="delete" onClick={() => handleEliminarProducto(index)}>X</Button>
                </li>
              ))}
            </ul>
          </div>

          {/* Panel derecho: Formulario */}
          {cajaAbierta ? (
            <FormVentas
              onAgregarProducto={handleAgregarProducto}
              totalVenta={totalVenta}
              productosVendidos={productos}
              onLimpiarResumen={limpiarResumen}
            />
          ) : (
            <div className="flex justify-center items-center w-full p-8 bg-yellow-100 border border-yellow-300 rounded-lg text-yellow-800 font-semibold text-xl">
              La caja está cerrada. Debes abrirla para comenzar a registrar ventas.
            </div>
          )}
        </div>

      </div>
    </ProtectedRoute>
  );
}

export default DashboardVenta;