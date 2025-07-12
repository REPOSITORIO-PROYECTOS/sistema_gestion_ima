"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import FormVentas from "./FormVentas";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuthStore } from "@/lib/authStore";

function DashboardVenta() {

  const [productos, setProductos] = useState<{ tipo: string; cantidad: number; precioTotal: number }[]>([]);
  const [fechaActual, setFechaActual] = useState("");
  const [horaActual, setHoraActual] = useState("");

  // Traemos el rol desde Zustand
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

    const interval = setInterval(updateDateTime, 60 * 1000); // cada 1 minuto

    return () => clearInterval(interval);
  }, []);

  // Mapeamos el rol para mostrarlo legible
  const mostrarRol = () => {
    if (role === "admin") return "Administrador";
    if (role === "cajero") return "Cajero";
    return "Rol no identificado";
  };

  const totalVenta = productos.reduce((acc, prod) => acc + prod.precioTotal, 0);

  const handleAgregarProducto = (producto: { tipo: string; cantidad: number; precioTotal: number }) => {
    setProductos((prev) => [...prev, producto]);
  };

  const handleEliminarProducto = (index: number) => {
    setProductos((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <ProtectedRoute allowedRoles={["admin", "cajero"]}>
      <div className="flex flex-col gap-4">

        {/* Barra de Información */}
        <div className="flex flex-wrap justify-between items-center p-4 gap-4 bg-neutral-800/90 rounded-xl">
          <Input
            value={fechaActual}
            disabled
            className="w-full sm:w-[48%] lg:w-[23%] text-white font-semibold border border-white bg-transparent placeholder-white disabled:opacity-100 rounded-lg"
          />
          <Input
            value={horaActual}
            disabled
            className="w-full sm:w-[48%] lg:w-[23%] text-white font-semibold border border-white bg-transparent placeholder-white disabled:opacity-100 rounded-lg"
          />
          <Input
            value={mostrarRol()}
            disabled
            className="w-full sm:w-[48%] lg:w-[23%] text-white font-semibold border border-white bg-transparent placeholder-white disabled:opacity-100 rounded-lg"
          />
          <Button
            className="w-full sm:w-[48%] lg:w-[23%] text-white font-semibold p-2 text-center border rounded-lg border-white hover:bg-white transition hover:text-green-800"
            onClick={() => console.log("Abrir modal de historial")}
          >
            Historial de Pedidos
          </Button>
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
                  className="flex flex-row w-full justify-between items-center px-8 py-6 bg-green-600 rounded-lg text-white text-xl shadow-lg"
                >
                  <div>
                    {prod.tipo} - x{prod.cantidad} - ${prod.precioTotal}
                  </div>
                  <Button variant="delete" onClick={() => handleEliminarProducto(index)}>X</Button>
                </li>
              ))}
            </ul>
          </div>

          {/* Panel derecho: Formulario */}
          <FormVentas
            onAgregarProducto={handleAgregarProducto}
            totalVenta={totalVenta}
            productosVendidos={productos}
          />
        </div>
      </div>
    </ProtectedRoute>
  );
}

export default DashboardVenta;