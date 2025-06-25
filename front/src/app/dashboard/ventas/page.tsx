"use client"

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import FormVentas from "./FormVentas";
import { useState } from "react";

/* -------------------------------------------- PANEL VENTAS -------------------------------------------- */

function DashboardVenta() {

  /* Funcion para añadir items al panel de productos principal */

  // Estado del panel de productos
  const [productos, setProductos] = useState<{ tipo: string; cantidad: number; precioTotal: number }[]>([]);

  // Agrega un producto al array de productos seleccionados
  const handleAgregarProducto = (producto: { tipo: string; cantidad: number; precioTotal: number }) => {
  setProductos(prev => [...prev, producto]);
  };

  // Elimina un producto del panel por índice
  const handleEliminarProducto = (index: number) => {
    setProductos(prev => prev.filter((_, i) => i !== index));
  };

  // Estado de TODOS los productos - sumatoria
  const totalVenta = productos.reduce((acc, prod) => acc + prod.precioTotal, 0);

  
  return (
    
    <div className="flex flex-col gap-4">

      {/* Barra Información */}
      <div className="flex flex-row justify-between items-center p-4 gap-6 bg-neutral-800/90 rounded-xl">
        <Input defaultValue="23/03/2025" disabled
          className="w-1/3 text-white font-semibold border border-white bg-transparent placeholder-white disabled:opacity-100 rounded-lg" />
        <Input defaultValue="14:32" disabled
          className="w-1/3 text-white font-semibold border border-white bg-transparent placeholder-white disabled:opacity-100 rounded-lg" />
        <Input defaultValue="Cajero Asignado" disabled
          className="w-1/3 text-white font-semibold border border-white bg-transparent placeholder-white disabled:opacity-100 rounded-lg" />
        <a href="" className="w-1/3 text-white font-semibold p-2 text-center border rounded-lg border-white hover:bg-white transition hover:text-green-800">
          Historial de Pedidos
        </a>
      </div>


      {/* Bloque Form Cajero + Resumen de Productos */}
      <div className="flex flex-row justify-between gap-4">


        {/* Resumen de Productos (panel izquierdo) */}
        <div className="flex flex-col items-start w-1/2 bg-gray-100 rounded-xl shadow-md">
    
          {/* Header del Resumen Productos */}
          <div className="w-full flex flex-row justify-between items-center p-6 bg-green-700 rounded-t-xl">
            <h4 className="text-xl font-semibold text-white">Resumen del Pedido</h4>
            <p className="text-2xl font-semibold text-white">Total: ${totalVenta}</p>
          </div>
          
          {/* Lista de productos agregados */}
          <ul className="flex flex-col items-center w-full p-6 gap-5 overflow-y-auto ">
            {productos.map((prod, index) => (
              <li key={index} className="flex flex-row w-full justify-between items-center px-8 py-6 bg-green-600 rounded-lg text-white text-xl shadow-lg">
                <div>{prod.tipo} - x{prod.cantidad} - ${prod.precioTotal}</div>
                <Button variant="delete" onClick={() => handleEliminarProducto(index)}>X</Button>
              </li>
            ))}
          </ul>
        </div>


        {/* Formulario de Ventas */}
        <FormVentas
          onAgregarProducto={handleAgregarProducto}
          totalVenta={totalVenta}
          productosVendidos={productos}
        />

          
      </div>

    </div>
  )
}

export default DashboardVenta;