"use client";

import { useEffect, useState, useCallback } from "react";
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
import { useFacturacionStore } from "@/lib/facturacionStore"; // Importar
import EgresoForm from "./EgresoForm";

interface ProductoVendido {
  tipo: string;
  cantidad: number;
  precioTotal: number;
  precioBase: number;
  descuentoAplicado?: boolean;
  porcentajeDescuento?: number; // %
  descuentoNominal?: number;    // $
}

function DashboardVenta() {

  /* Estados de la Caja de Ventas */
  const verificarEstadoCaja = useCajaStore(state => state.verificarEstadoCaja);
  const token = useAuthStore((state) => state.token);
  const [productos, setProductos] = useState<ProductoVendido[]>([]);
  const [fechaActual, setFechaActual] = useState("");
  const [horaActual, setHoraActual] = useState("");
  const { cajaAbierta } = useCajaStore();
  const role = useAuthStore((state) => state.role);

  // Estados movidos desde FormVentas
  const [descuentoSobreTotal, setDescuentoSobreTotal] = useState(0);
  const [descuentoNominalTotal, setDescuentoNominalTotal] = useState(0);
  const [metodoPago, setMetodoPago] = useState("efectivo");
  const [montoPagado, setMontoPagado] = useState<number>(0);
  const [vuelto, setVuelto] = useState<number>(0);
  const { recargoTransferenciaActivo, recargoTransferencia, recargoBancarioActivo, recargoBancario } = useFacturacionStore();


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
      verificarEstadoCaja(token);
    }
  }, [token, verificarEstadoCaja]);

  // Mapeamos el rol para mostrarlo legible en el panel de informacion
  const mostrarRol = () => {
    if (role?.nombre === "Admin") return "Administrador";
    if (role?.nombre === "Cajero") return "Cajero";
    if (role?.nombre === "Gerente") return "Gerente";
    if (role?.nombre === "Soporte") return "Soporte";
    return "Rol no identificado";
  };

  const totalVenta = productos.reduce((acc, prod) => acc + prod.precioTotal, 0);

  // Lógica de cálculo de total final movida aquí
  const totalConDescuento = Math.max(0, totalVenta * (1 - descuentoSobreTotal / 100) - descuentoNominalTotal);

  const totalVentaFinal = (() => {
    let total = totalConDescuento;
    if (metodoPago === "transferencia" && recargoTransferenciaActivo) {
      total += total * (recargoTransferencia / 100);
    } else if (metodoPago === "bancario" && recargoBancarioActivo) {
      total += total * (recargoBancario / 100);
    }
    return Math.round(total * 100) / 100;
  })();

  useEffect(() => {
    if (metodoPago === "efectivo" && typeof montoPagado === "number" && !isNaN(montoPagado)) {
      const cambio = montoPagado - totalVentaFinal;
      setVuelto(cambio >= 0 ? cambio : 0);
    } else {
      setVuelto(0);
    }
  }, [montoPagado, metodoPago, totalVentaFinal]);

  const handleAgregarProducto = useCallback((
    producto: {
      tipo: string;
      cantidad: number;
      precioTotal: number;
      precioBase: number;
      descuentoAplicado: boolean;
      porcentajeDescuento: number;
      descuentoNominal: number;
    }
  ) => { setProductos((prev) => [...prev, producto]); }, []);

  const handleUpdateProductDiscount = useCallback((index: number, type: 'porcentaje' | 'nominal', value: number) => {
    setProductos(prev => {
      const newProductos = [...prev];
      const prod = { ...newProductos[index] };

      if (type === 'porcentaje') {
        prod.porcentajeDescuento = value;
      } else {
        prod.descuentoNominal = value;
      }

      // Recalculate
      const base = prod.precioBase;
      const descPorc = prod.porcentajeDescuento || 0;
      const descNom = prod.descuentoNominal || 0;

      const subtotal = base * (1 - descPorc / 100);
      prod.precioTotal = Math.max(0, subtotal - descNom);
      prod.descuentoAplicado = descPorc > 0 || descNom > 0;

      newProductos[index] = prod;
      return newProductos;
    });
  }, []);

  const handleEliminarProducto = useCallback((index: number) => {
    setProductos((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const limpiarResumen = useCallback(() => {
    setProductos([]);
    setDescuentoNominalTotal(0);
    setDescuentoSobreTotal(0);
    setMontoPagado(0);
    setVuelto(0);
  }, []);

  // Formateo del total de venta
  const formatearMoneda = (valor: number): string => {
    return valor.toLocaleString("es-AR", {
      style: "currency",
      currency: "ARS",
      minimumFractionDigits: 2,
    });
  };


  return (
    <ProtectedRoute allowedRoles={["Admin", "Cajero", "Soporte"]}>
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
                onAbrirCaja={() => { }}
                onCerrarCaja={() => { }}
              />
            </DialogContent>
          </Dialog>
        </div>

        {/* Bloque principal: Resumen + Formulario */}
        <div className="flex flex-col-reverse md:flex-row justify-between gap-4">

          {/* Panel izquierdo: Resumen */}
          <div className="flex flex-col items-start w-full lg:w-1/2 md:max-w-2/3 bg-gray-100 rounded-xl shadow-md">

            {/* Header */}
            <div className="w-full flex flex-row justify-between items-center px-6 py-4 bg-green-700 rounded-t-xl">
              <h4 className="text-xl font-semibold text-white">Resumen del Pedido</h4>
            </div>

            {/* Render de los Productos */}
            <ul className="flex flex-col items-center w-full p-6 gap-5 overflow-y-auto max-h-[50vh]">
              {productos.map((prod, index) => (
                <li
                  key={index}
                  className="flex flex-col md:flex-row w-full justify-between items-start md:items-center px-6 py-4 bg-emerald-100 rounded-lg text-green-950 font-semibold border-3 border-green-800 text-xl shadow-lg"
                >
                  <div className="flex flex-col w-full gap-2">
                    <span>{prod.tipo} - x{prod.cantidad} U. - {formatearMoneda(prod.precioTotal)}</span>

                    <div className="flex flex-row gap-4 items-center mt-1">
                      <div className="flex flex-col w-24">
                        <label className="text-xs font-normal text-green-800">Desc %</label>
                        <Input
                          type="number"
                          min={0}
                          max={100}
                          value={prod.porcentajeDescuento || 0}
                          onChange={(e) => handleUpdateProductDiscount(index, 'porcentaje', parseFloat(e.target.value) || 0)}
                          className="h-8 text-sm bg-white"
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                      <div className="flex flex-col w-24">
                        <label className="text-xs font-normal text-green-800">Desc $</label>
                        <Input
                          type="number"
                          min={0}
                          value={prod.descuentoNominal || 0}
                          onChange={(e) => handleUpdateProductDiscount(index, 'nominal', parseFloat(e.target.value) || 0)}
                          className="h-8 text-sm bg-white"
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                    </div>
                  </div>

                  <Button variant="delete" onClick={() => handleEliminarProducto(index)}>X</Button>
                </li>
              ))}
            </ul>

            {/* Resumen de toda la Venta */}
            <div className="w-full p-4 border-t border-gray-300">
              <div className="flex flex-col gap-4 p-6 bg-white border border-green-900 rounded-lg">
                <h3 className="text-2xl font-semibold text-green-900">Resumen Final del Pedido</h3>
                <p className="text-xl text-green-900"><span className="font-semibold">Total sin descuento:</span> {formatearMoneda(totalVenta)}</p>
                <div className="flex flex-col gap-2 my-2">
                  <div className="flex flex-row items-center justify-between gap-4">
                    <span className="text-xl text-green-400 font-semibold">Descuento Global (%):</span>
                    <Input
                      type="number"
                      min={0}
                      max={100}
                      value={descuentoSobreTotal === 0 ? '' : descuentoSobreTotal}
                      onChange={(e) => setDescuentoSobreTotal(Math.min(parseFloat(e.target.value) || 0, 100))}
                      className="w-32 h-10 text-lg text-right"
                      placeholder="0"
                    />
                  </div>
                  <div className="flex flex-row items-center justify-between gap-4">
                    <span className="text-xl text-green-400 font-semibold">Descuento Global ($):</span>
                    <Input
                      type="number"
                      min={0}
                      value={descuentoNominalTotal === 0 ? '' : descuentoNominalTotal}
                      onChange={(e) => setDescuentoNominalTotal(parseFloat(e.target.value) || 0)}
                      className="w-32 h-10 text-lg text-right"
                      placeholder="0.00"
                    />
                  </div>
                </div>

                {metodoPago === "transferencia" && recargoTransferenciaActivo && (
                  <p className="text-xl text-red-500"><span className="font-semibold">Recargo por Transferencia:</span> {recargoTransferencia}% ({formatearMoneda(totalConDescuento * recargoTransferencia / 100)})</p>
                )}
                {metodoPago === "bancario" && recargoBancarioActivo && (
                  <p className="text-xl text-red-500"><span className="font-semibold">Recargo por POS:</span> {recargoBancario}% ({formatearMoneda(totalConDescuento * recargoBancario / 100)})</p>
                )}

                <span className="block w-full h-0.5 bg-green-900 my-2"></span>
                <p className="text-2xl font-bold text-green-900"><span className="font-semibold">Valor Final del Pedido:</span> {formatearMoneda(totalVentaFinal)}</p>

                {metodoPago === "efectivo" && montoPagado > 0 && (
                  <p className="text-xl text-emerald-700 font-semibold">Vuelto para el cliente: {formatearMoneda(vuelto)}</p>
                )}
              </div>
            </div>
          </div>

          {/* Panel derecho: Formulario */}
          {cajaAbierta ? (
            <FormVentas
              onAgregarProducto={handleAgregarProducto}
              totalVenta={totalVenta}
              productosVendidos={productos}
              onLimpiarResumen={limpiarResumen}
              descuentoSobreTotal={descuentoSobreTotal}
              setDescuentoSobreTotal={setDescuentoSobreTotal}
              descuentoNominalTotal={descuentoNominalTotal}
              setDescuentoNominalTotal={setDescuentoNominalTotal}
              metodoPago={metodoPago}
              setMetodoPago={setMetodoPago}
              totalVentaFinal={totalVentaFinal}
              vuelto={vuelto}
              montoPagado={montoPagado}
              setMontoPagado={setMontoPagado}
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