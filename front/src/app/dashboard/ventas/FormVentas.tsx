"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue
} from "@/components/ui/select"

// Dropdown Productos
const productos = [
  { id: "1", nombre: "Jugo de Naranja", precio: 500 },
  { id: "2", nombre: "Jugo de Durazno", precio: 600 },
  { id: "3", nombre: "Jugo de Manzana", precio: 400 },
  { id: "4", nombre: "Disecado de Naranja (0.5 Kg)", precio: 400 },
  { id: "5", nombre: "Disecado de Durazno (0.5 Kg)", precio: 400 },
]

// Dropdown tipo de cliente
const tipoCliente = [
  { id: "1", nombre: "Con CUIT"},       // este anda
  { id: "2", nombre: "Cliente Final"},  // este no
]

function FormVentas({
  onAgregarProducto,    /* Agrega productos al resumen - no es el submit */
  totalVenta,           /* Valor total de todos los productos - costo total del pedido */
  productosVendidos     /* Lista con todos los productos vendidos y su cantidad */
}: {
  onAgregarProducto: (prod: { tipo: string; cantidad: number; precioTotal: number }) => void,
  totalVenta: number,
  productosVendidos: { tipo: string; cantidad: number; precioTotal: number }[]
}) {

  // Listado de productos - para nuevos prod, agregar en el array de arriba
  const [productoSeleccionado, setProductoSeleccionado] = useState(productos[0])
  
  // Cantidad de un producto particular - se * por el producto y se saca el valor total
  const [cantidad, setCantidad] = useState(1)
  
  // Producto seleccionado * cantidad = total
  const totalProducto = productoSeleccionado.precio * cantidad

  /* -------------------------------------------------------------- */

  // Sección Facturación 
  const [tipoClienteSeleccionado, setTipoClienteSeleccionado] = useState(tipoCliente[1])
  const [metodoPago, setMetodoPago] = useState("efectivo")

  // Estados para la opcion de efectivo y vuelto
  const [montoPagado, setMontoPagado] = useState<number>(0);
  const [vuelto, setVuelto] = useState<number>(0);

  // Estado para las observaciones de la venta
  const [observaciones, setObservaciones] = useState("")

  /* -------------------------------------------------------------- */

  // Hook para agregar producto al panel resumen de productos
  const handleAgregarProducto = () => {
    onAgregarProducto({
      tipo: productoSeleccionado.nombre,
      cantidad,
      precioTotal: totalProducto,
    });

    // Reseteamos cantidad a 1 por default luego de agregar
    setCantidad(1);
  }

  // Hook para mostrar la calculadora de vuelto si se selecciona efectivo
  useEffect(() => {
    if (metodoPago === 'efectivo' && typeof montoPagado === 'number') {
      const cambio = montoPagado - totalProducto;
      setVuelto(cambio >= 0 ? cambio : 0);
    } else {
      setVuelto(0);
    }
  }, [montoPagado, totalProducto, metodoPago]);

  // Estado para el cambio en efectivo en base al valor final
  useEffect(() => {
    if (metodoPago === "efectivo") {
      const calculado = montoPagado - totalVenta;
      setVuelto(calculado > 0 ? calculado : 0);
    } else {
      setVuelto(0);
    }
  }, [montoPagado, metodoPago, totalVenta]);



  // Registrar la venta completa - falta terminar
  const handleSubmit = async (e: React.FormEvent) => {

    e.preventDefault();
  
    // Objeto resumen de toda la venta generada
    const ventaPayload = {
      id_sesion_caja: 3,
      id_cliente: tipoClienteSeleccionado.id,     // con "1" funciona, con "2" no
      usuario: "admin",
      id_usuario: 1,                              // debe ser dinamico con el tipo de usuario / admin=1, cajero=2, etc
      metodo_pago: metodoPago.toUpperCase(),
      total_venta: totalVenta,
      /* paga_con: metodoPago === "efectivo" ? montoPagado : undefined, */  // probar si anda CON esto
      quiere_factura: true,
      tipo_comprobante_solicitado: "Ticket No Fiscal",    // o según la selección de ticket/comprobante
      articulos_vendidos: productosVendidos.map((p) => {
        const productoReal = productos.find(prod => prod.nombre === p.tipo);
        return {
          id_articulo: productoReal?.id ?? "0",
          nombre: productoReal?.nombre ?? p.tipo,
          cantidad: p.cantidad,
          precio_unitario: productoReal?.precio ?? 0,
          subtotal: p.precioTotal,
          tasa_iva: 21.0                      // IVA 21%?
        };
      })
    };

    try {
      const response = await fetch("https://sistema-ima.sistemataup.online/api/caja/ventas/registrar", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(ventaPayload)
      });

      if (response.ok) {

        const data = await response.json();
        alert("✅ Venta registrada exitosamente: " + data.message);

      } else {

        const error = await response.json();
        alert("❌ Error al registrar venta: " + error.detail);
      }
    } catch (error) {

      console.error("Detalles del error:", error);
      alert("❌ Error al registrar venta:\n" + JSON.stringify(error, null, 2));
    }

    // Verificamos que estamos mandando
    console.log(JSON.stringify(ventaPayload, null, 2));
  };

  

  return (
    <form onSubmit={handleSubmit} 
    className="flex flex-col w-1/2 rounded-xl bg-white shadow-md">

      {/* Header del Cajero */}
      <div className="w-full flex flex-row justify-between items-center p-6 bg-green-700 rounded-t-xl">
        <h4 className="text-2xl font-semibold text-white">Cajero</h4>
      </div>

      <div className="flex flex-col justify-between w-full gap-6 p-8">

        {/* Listado de Productos */}
        <div className="flex flex-row gap-4 items-center justify-between">
          <Label className="text-2xl font-semibold text-green-900">Producto</Label>
          <Select
            defaultValue={productoSeleccionado.id}
            onValueChange={(value) => {
              const prod = productos.find(p => p.id === value)
              if (prod) setProductoSeleccionado(prod)
            }}>
            <SelectTrigger className="w-1/2 cursor-pointer text-black">
              <SelectValue placeholder="Seleccionar producto" />
            </SelectTrigger>
            <SelectContent>
              {productos.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.nombre} - ${p.precio}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>


        {/* Cantidad de un Producto */}
        <div className="flex flex-row gap-4 items-center justify-between">
          <Label className="text-2xl font-semibold text-green-900">Cantidad</Label>
          <Input
            type="number"
            min={1}
            value={cantidad}
            onChange={(e) => setCantidad(Number(e.target.value))}
            className="w-1/2 text-black"
          />
        </div>


        {/* Total de prod * cant */}
        <div className="flex flex-row gap-4 justify-between items-center mt-4">
          <Label className="text-2xl font-semibold text-green-900">Total</Label>
          <p className="text-2xl font-semibold text-green-900">${totalProducto}</p>
        </div>


        {/* Botón Agregar Producto */}
        <Button
          type="button"
          onClick={handleAgregarProducto}
          className="bg-green-900 hover:bg-green-700"
        >
          Agregar producto
        </Button>

        {/* --------------------------------------- */} <hr className="p-0.25 bg-green-900"/> {/* --------------------------------------- */}


        {/* Tipo Cliente */}
        <div className="flex flex-row gap-4 items-center justify-between">
          <Label className="text-2xl font-semibold text-green-900">Tipo de Cliente</Label>
          <Select
            defaultValue={tipoClienteSeleccionado.id}
            onValueChange={(value) => {
              const cliente = tipoCliente.find(p => p.id === value)
              if (cliente) setTipoClienteSeleccionado(cliente)
            }}>
            <SelectTrigger className="w-1/2 cursor-pointer text-black">
              <SelectValue placeholder="Seleccionar cliente" />
            </SelectTrigger>
            <SelectContent>
              {tipoCliente.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.nombre}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>


        {/* Método de Pago y condicional efectivo */}
        <div className="flex flex-col gap-4">
          <div className="flex flex-row gap-4 items-center justify-between">
            <Label className="text-2xl font-semibold text-green-900">Método de Pago</Label>
            <Select
              value={metodoPago}
              onValueChange={(value) => setMetodoPago(value)}
            >
              <SelectTrigger className="w-1/2 cursor-pointer text-black">
                <SelectValue placeholder="Seleccionar método" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="efectivo">Efectivo</SelectItem>
                <SelectItem value="transferencia">Transferencia</SelectItem>
                <SelectItem value="credito">Crédito</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {metodoPago === 'efectivo' && (
            <div className="flex flex-col gap-4 p-4 bg-green-800 rounded-lg mt-2">
              <div className="flex flex-row gap-4 items-center justify-between">
                <Label className="text-2xl font-semibold text-white">Con cuánto paga</Label>
                <Input
                  type="number"
                  min={totalVenta}
                  value={montoPagado}
                  onChange={(e) => setMontoPagado(Number(e.target.value))}
                  className="w-1/2 text-white"
                />
              </div>
              <div className="flex flex-row gap-4 items-center justify-between">
                <Label className="text-2xl font-semibold text-white">Cambio</Label>
                <Input
                  type="number"
                  value={vuelto}
                  disabled
                  className="w-1/2 text-white bg-green-900"
                />
              </div>
            </div>
          )}
        </div>


        {/* Checkbox Ticket o Comprobante */}
        <RadioGroup defaultValue="ticket" className="flex flex-row gap-4">
          
          {/* Ticket */}
          <Label
            htmlFor="ticket"
            className="flex flex-row items-center w-1/2 cursor-pointer text-black border-green-900 hover:bg-green-400 dark:hover:bg-green-700 gap-3 rounded-lg border p-3 transition-colors duration-200 data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900"
          >
            <RadioGroupItem
              value="ticket"
              id="ticket"
              className="data-[state=checked]:border-white data-[state=checked]:bg-white"
            />
            <span className="text-sm leading-none font-medium">Ticket</span>
          </Label>
          
          {/* Comprobante */}
          <Label
            htmlFor="comprobante"
            className="flex flex-row items-center w-1/2 cursor-pointer text-black border-green-900 hover:bg-green-400 dark:hover:bg-green-700 gap-3 rounded-lg border p-3 transition-colors duration-200 data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900"
          >
            <RadioGroupItem
              value="comprobante"
              id="comprobante"
              className="data-[state=checked]:border-white data-[state=checked]:bg-white"
            />
            <span className="text-sm leading-none font-medium">Comprobante</span>
          </Label>
        </RadioGroup>


        {/* Observaciones */}
        <div className="flex flex-col w-full gap-2">
          <Label className="text-green-900 text-xl" htmlFor="message-2">Observaciones</Label>
          <Textarea
            placeholder="Observaciones.."
            id="message-2"
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
          />
        </div>


        {/* Total Venta */}
        <div className="flex flex-row gap-4 justify-between items-center mt-4 px-2">
          <Label className="text-2xl font-semibold text-green-900">Total del Pedido</Label>
          <p className="text-3xl font-semibold text-green-900">${totalVenta}</p>
        </div>


        {/* Botón Final: Registrar Venta y enviar toda la info al server */}
        <Button type="submit" className="bg-green-900 hover:bg-green-700">
          Registrar Venta
        </Button>

      </div>

    </form>
  );
}

export default FormVentas;