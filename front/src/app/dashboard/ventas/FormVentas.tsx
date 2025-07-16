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
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "@/components/ui/command";
import { ChevronsUpDown } from "lucide-react";

interface ProductoAPI {
  id: number;
  descripcion: string;
  precio_venta: number;
  venta_negocio: number;
}

// Dropdown tipo de cliente
const tipoCliente = [
  { id: "1", nombre: "Con CUIT"},      
  { id: "2", nombre: "Cliente Final"}, 
]

function FormVentas({
  onAgregarProducto,    /* Agrega productos al resumen (componente padre) */
  totalVenta,           /* Valor total de todos los productos - costo total del pedido */
  productosVendidos     /* Lista con todos los productos vendidos y su cantidad */
}: {
  onAgregarProducto: (prod: { tipo: string; cantidad: number; precioTotal: number }) => void,
  totalVenta: number,
  productosVendidos: { tipo: string; cantidad: number; precioTotal: number }[]
}) {

  /* Estados */

  // Listado de productos - GET 
  const [productos, setProductos] = useState<{
    id: string;
    nombre: string;
    precio_venta: number;
    venta_negocio: number;
  }[]>([]);

  // Necesario para clasificar precios segun cliente
  const [productoSeleccionado, setProductoSeleccionado] = useState<{
    id: string;
    nombre: string;
    precio_venta: number;
    venta_negocio: number;
  } | null>(null);

  // Cantidad de un producto particular - se * por el producto y se saca el valor total
  const [cantidad, setCantidad] = useState(1)

  // Input de Busqueda para Productos
  /* const [searchProducto, setSearchProducto] = useState(""); */
  const [open, setOpen] = useState(false);


  // Sección Facturación 
  const [tipoClienteSeleccionado, setTipoClienteSeleccionado] = useState(tipoCliente[1])
  const [metodoPago, setMetodoPago] = useState("efectivo")

  // Estados para la opcion de efectivo y vuelto
  const [montoPagado, setMontoPagado] = useState<number>(0);
  const [vuelto, setVuelto] = useState<number>(0);

  // Estado para las observaciones de la venta
  const [observaciones, setObservaciones] = useState("")

  // Estado animación para spinner de carga submit
  const [isLoading, setIsLoading] = useState(false);


  /* Hooks */ /* -------------------------------------------------------------- */

  // Producto seleccionado * cantidad = total
  const getPrecioProducto = (producto: {
    id: string;
    nombre: string;
    precio_venta: number;
    venta_negocio: number;
  } | null): number => {
    if (!producto) return 0;
    return tipoClienteSeleccionado.id === "1"
      ? producto.venta_negocio
      : producto.precio_venta;
  };

  const totalProducto = productoSeleccionado ? getPrecioProducto(productoSeleccionado) * cantidad : 0;

  // Hook para agregar producto al panel resumen de productos
  const handleAgregarProducto = () => {

    if (!productoSeleccionado) return; // Protege contra null

    onAgregarProducto({
      tipo: productoSeleccionado.nombre,
      cantidad,
      precioTotal: totalProducto,
    });

    setCantidad(1);
  };

  // Effect para mostrar la calculadora de vuelto si es pago con efectivo
  useEffect(() => {
    if (metodoPago === 'efectivo' && typeof montoPagado === 'number') {
      const cambio = montoPagado - totalProducto;
      setVuelto(cambio >= 0 ? cambio : 0);
    } else {
      setVuelto(0);
    }
  }, [montoPagado, totalProducto, metodoPago]);

  // Effect para el calculo del vuelto en pago con efectivo
  useEffect(() => {
    if (metodoPago === "efectivo") {
      const calculado = montoPagado - totalVenta;
      setVuelto(calculado > 0 ? calculado : 0);
    } else {
      setVuelto(0);
    }
  }, [montoPagado, metodoPago, totalVenta]);


  /* Endpoints */ /* -------------------------------------------------------------- */

  // GET Productos - trae los productos reales de la empresa
  useEffect(() => {

    const fetchProductos = async () => {

      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/articulos/obtener_todos");
        const data: ProductoAPI[] = await res.json();
        console.log(data)

        const productosMapeados = data.map((item) => ({
          id: String(item.id),
          nombre: item.descripcion,
          precio_venta: item.precio_venta,
          venta_negocio: item.venta_negocio,
        }));

        setProductos(productosMapeados);

        // Setear el primer producto como seleccionado por defecto
        if (productosMapeados.length > 0) {
          setProductoSeleccionado(productosMapeados[0]);
        }

      } catch (error) {
        console.error("❌ Error al obtener productos:", error);
      }
    };
    
    fetchProductos();
  }, []);

  // POST Ventas - Registra la venta completa
  const handleSubmit = async (e: React.FormEvent) => {

    if (productosVendidos.length === 0) {
      toast.error("❌ No hay productos cargados en la venta.");
      setIsLoading(false);
      return;
    }

    // Animacion de carga
    setIsLoading(true);
    e.preventDefault();
  
    // Objeto resumen de toda la venta generada
    const ventaPayload = {
      id_sesion_caja: 3,
      id_cliente: 8,            // reemplazar por cliente posta
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
          precio_unitario: productoReal ? getPrecioProducto(productoReal) : 0,
          subtotal: p.precioTotal,
          tasa_iva: 21.0                     
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
        toast.success("✅ Venta registrada: " + data.message);

      } else {

        const error = await response.json();
        toast.error("❌ Error al registrar venta: " + error.detail);
      }
    } catch (error) {

      console.error("Detalles del error:", error);
      alert("❌ Error al registrar venta:\n" + JSON.stringify(error, null, 2));

    } finally { setIsLoading(false); }

    // Se printea el Payload para debug
    console.log(JSON.stringify(ventaPayload, null, 2));
  };

  /* -------------------------------------------------------------- */

  return (              // TO DO  ->>>>>>>>>>> FORZAR EN LOS INPUTS QUE NO SE PUEDA MANDAR ALGO VACIO 

    <form onSubmit={handleSubmit} 
    className="flex flex-col w-full lg:w-1/2 rounded-xl bg-white shadow-md">

      {/* Header del Cajero */}
      <div className="w-full flex flex-row justify-between items-center p-6 bg-green-700 rounded-t-xl">
        <h4 className="text-2xl font-semibold text-white">Cajero</h4>
        <p className="text-2xl font-semibold text-white md:hidden">${totalVenta}</p>
      </div>

      <div className="flex flex-col justify-between w-full gap-6 p-8">

        {/* Tipo Cliente */}
        <div className="flex flex-col gap-4 items-start md:items-center justify-between md:flex-row">
          <Label className="text-2xl font-semibold text-green-900">Tipo de Cliente</Label>
          <div className="flex flex-col gap-2 w-full">
            <Select
              defaultValue={tipoClienteSeleccionado.id}
              onValueChange={(value) => {
                const cliente = tipoCliente.find(p => p.id === value)
                if (cliente) setTipoClienteSeleccionado(cliente)
              }}>
              <SelectTrigger className="w-full cursor-pointer text-black">
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
            {/* Input de busqueda si es cliente con CUIT */}
            {tipoClienteSeleccionado.id === "1" && (
              <Input
                type="text"
                placeholder="Buscar cliente por CUIT o nombre..."
                className="w-full text-black"
              />
            )}
          </div>
          
        </div>
        <span className="block w-full h-0.5 bg-green-900"></span>

        {/* Listado de Productos */}
        <div className="flex flex-col gap-4 items-start justify-between md:flex-row md:items-center">
          <Label className="text-2xl font-semibold text-green-900">Producto</Label>

          {!productoSeleccionado ? (
            <p className="text-green-900 font-semibold">Cargando productos...</p>
          ) : (
            <div className="w-full md:max-w-2/3 flex flex-col gap-2">
              <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                  <button
                    role="combobox"
                    aria-controls="productos-list"
                    aria-expanded={open}
                    className="w-full justify-between text-left cursor-pointer border px-3 py-2 rounded-md shadow-sm bg-white text-black flex items-center"
                    onClick={() => setOpen(!open)}
                  >
                    {productoSeleccionado
                      ? `${productoSeleccionado.nombre} - $${tipoClienteSeleccionado.id === "1"
                          ? productoSeleccionado.venta_negocio
                          : productoSeleccionado.precio_venta}`
                      : "Seleccionar producto"}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </button>
                </PopoverTrigger>
                <PopoverContent
                  side="bottom"
                  align="start"
                  className="w-full md:max-w-[98%] p-0 max-h-64 overflow-y-auto z-50"
                  sideOffset={8} 
                >
                  <Command>
                    <CommandInput placeholder="Buscar producto..." />
                    <CommandEmpty>No se encontró ningún producto.</CommandEmpty>
                    <CommandGroup>
                      {productos.map((p) => (
                        <CommandItem
                          key={p.id}
                          value={p.nombre}
                          className="pl-2 pr-4 py-2 text-sm text-black cursor-pointer"
                          onSelect={() => {
                            setProductoSeleccionado(p);
                            setOpen(false);
                          }}
                        >
                          <span className="truncate">
                            {p.nombre} - ${tipoClienteSeleccionado.id === "1" ? p.venta_negocio : p.precio_venta}
                          </span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>
          )}
        </div>

        {/* Cantidad de un Producto */}
        <div className="flex flex-col gap-4 items-start justify-between md:flex-row">
          <Label className="text-2xl font-semibold text-green-900">Cantidad</Label>
          <Input
            type="number"
            min={1}
            value={cantidad}
            onChange={(e) => setCantidad(Number(e.target.value))}
            className="w-full md:max-w-1/2 text-black"
          />
        </div>
        <span className="block w-full h-0.5 bg-green-900"></span>


        {/* Total de prod * cant */}
        <div className="flex flex-row gap-4 justify-between items-start mt-4">
          <Label className="text-2xl font-semibold text-green-900">Total</Label>
          <p className="text-2xl font-semibold text-green-900">${totalProducto}</p>
        </div>


        {/* Botón Agregar Producto */}
        <Button
          variant="success"
          type="button"
          onClick={() => {
            handleAgregarProducto();
            toast.success("Producto agregado al resumen.");
          }}
        >
          + Agregar producto
        </Button>

        {/* --------------------------------------- */} <hr className="p-0.75 bg-green-900 my-8"/> {/* --------------------------------------- */}


        {/* Método de Pago y condicional efectivo */}
        <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-4 items-start justify-between md:flex-row">
              <Label className="text-2xl font-semibold text-green-900">Método de Pago</Label>
              <Select
                value={metodoPago}
                onValueChange={(value) => setMetodoPago(value)}
              >
                <SelectTrigger className="w-full md:max-w-1/2 cursor-pointer text-black">
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
            /* Caja de Vuelto en Efectivo: */
            <div className="flex flex-col gap-4 p-4 bg-green-800 rounded-lg mt-2">
              <div className="flex flex-col md:flex-row gap-4 items-start justify-between">
                <Label className="text-2xl font-semibold text-white">Costo del Pedido:</Label>
                <Input
                  type="number"
                  value={totalVenta}
                  disabled
                  className="w-full md:max-w-1/2 font-semibold text-white"
                />
              </div>
              <div className="flex flex-col md:flex-row gap-4 items-start justify-between">
                <Label className="text-2xl font-semibold text-white">Con cuánto abona:</Label>
                <Input
                  type="number"
                  min={totalVenta}
                  value={montoPagado}
                  onChange={(e) => setMontoPagado(Number(e.target.value))}
                  className="w-full md:max-w-1/2 font-semibold text-white"
                />
              </div>
              <div className="flex flex-col md:flex-row gap-4 items-start justify-between">
                <Label className="text-2xl font-semibold text-white">Vuelto:</Label>
                <Input
                  type="number"
                  value={vuelto}
                  disabled
                  className="w-full md:max-w-1/2 font-semibold text-white"
                />
              </div>
            </div>
          )}
        </div>
        <span className="block w-full h-0.5 bg-green-900"></span>


        {/* Checkbox Ticket o Comprobante */}
        <RadioGroup defaultValue="ticket" className="flex flex-col gap-4 md:flex-row">
          
          {/* Ticket */}
          <Label
            htmlFor="ticket"
            className="flex flex-row items-center w-full md:w-1/2 lg:flex-row cursor-pointer text-black border-green-900 hover:bg-green-400 dark:hover:bg-green-700 gap-3 rounded-lg border p-3 transition-colors duration-200 data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900"
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
            className="flex flex-row items-center w-full md:w-1/2 lg:flex-row cursor-pointer text-black border-green-900 hover:bg-green-400 dark:hover:bg-green-700 gap-3 rounded-lg border p-3 transition-colors duration-200 data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900"
          >
            <RadioGroupItem
              value="comprobante"
              id="comprobante"
              className="data-[state=checked]:border-white data-[state=checked]:bg-white"
            />
            <span className="text-sm leading-none font-medium">Comprobante</span>
          </Label>
        </RadioGroup>
        <span className="block w-full h-0.5 bg-green-900"></span>


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

        {/* --------------------------------------- */} <hr className="p-0.75 bg-green-900 my-8"/> {/* --------------------------------------- */}

        {/* Total Venta */}
        <div className="flex flex-row gap-4 justify-between items-center px-2">
          <Label className="text-2xl font-semibold text-green-900">Total del Pedido</Label>
          <p className="text-3xl font-semibold text-green-900">${totalVenta}</p>
        </div>


        {/* Botón Final: Registra venta y envia toda la info al server */}
        <Button
            type="submit"
            disabled={isLoading}
            className={`bg-green-900 flex items-center justify-center gap-2
              ${isLoading 
                ? "cursor-not-allowed opacity-50"
                : "hover:bg-green-700 cursor-pointer"
              }
            `}
          >
            {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
            {isLoading ? "Registrando..." : "Registrar Venta"}
          </Button>

      </div>

    </form>
  );
}

export default FormVentas;