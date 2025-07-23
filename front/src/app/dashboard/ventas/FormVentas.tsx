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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import { ChevronsUpDown } from "lucide-react";
import { useFacturacionStore } from "@/lib/facturacionStore";


interface ProductoAPI {
  id: number;
  descripcion: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
}

type Cliente = {
  id: number;
  nombre_razon_social: string;
  condicion_iva: string;
  identificacion_fiscal: string | null;
  cuit: string | null;
  telefono: string;
  activo: boolean;
};

// Dropdown tipo de cliente
const tipoCliente = [
  { id: "0", nombre: "Cliente Final" },
  { id: "1", nombre: "Cliente con CUIT" },
  { id: "2", nombre: "Cliente sin CUIT" },
];

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
    stock_actual: number;
  }[]>([]);

  // Necesario para clasificar precios segun tipo de cliente
  const [productoSeleccionado, setProductoSeleccionado] = useState<{
    id: string;
    nombre: string;
    precio_venta: number;
    venta_negocio: number;
    stock_actual: number;
  } | null>(null);

  // Listado de Clientes - GET
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [clienteSeleccionado, setClienteSeleccionado] = useState<Cliente | null>(null);
  const [openCliente, setOpenCliente] = useState(false);

  // Ingresar el CUIT de un Cliente Final - POST
  const [cuitManual, setCuitManual] = useState("");

  /* 
    AGREGAR LOGICA DE REGISTRO? 
  */


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

  // Estado para la opción de facturación
  const [tipoFacturacion, setTipoFacturacion] = useState("factura");
  const { habilitarExtras } = useFacturacionStore();  



  /* Hooks */ /* -------------------------------------------------------------- */

  // Producto seleccionado * cantidad = total
  const getPrecioProducto = (producto: {
    id: string;
    nombre: string;
    precio_venta: number;
    venta_negocio: number;
  } | null): number => {
    if (!producto) return 0;

    // Cliente Final usa precio_venta siempre
    if (tipoClienteSeleccionado.id === "0") return producto.precio_venta;

    // Cliente con CUIT o sin CUIT
    return producto.venta_negocio;
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

  // GET Clientes - trae todos los clientes inscriptos
  useEffect(() => {
    const fetchClientes = async () => {
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/clientes/obtener-todos");
        const data: Cliente[] = await res.json();
        const clientesActivos = data.filter((cliente: Cliente) => cliente.activo);

        setClientes(clientesActivos);
        /* console.log("Clientes obtenidos:", clientesActivos); */    // solo debug
      } catch (error) {
        console.error("❌ Error al obtener clientes:", error);
      }
    };

    fetchClientes();
  }, []);

  // GET Productos - trae los productos reales de la empresa
  useEffect(() => {

    const fetchProductos = async () => {

      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/articulos/obtener_todos");
        const data: ProductoAPI[] = await res.json();
        
        /* console.log(data) */   // Solo debug

        const productosMapeados = data.map((item) => ({
          id: String(item.id),
          nombre: item.descripcion,
          precio_venta: item.precio_venta,
          venta_negocio: item.venta_negocio,
          stock_actual: item.stock_actual,
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

    if (metodoPago === "efectivo" && montoPagado < totalVenta) {
      toast.error("❌ El monto pagado no puede ser menor al total del pedido.");
      setIsLoading(false);
      return;
    }

    // Animacion de carga
    setIsLoading(true);
    e.preventDefault();
  
    // Objeto resumen de toda la venta generada
    const ventaPayload = {
      id_sesion_caja: 3,
      id_cliente:
        tipoClienteSeleccionado.id === "0"
          ? 8 // Cliente Final: ID fijo
          : clienteSeleccionado?.id ?? 8, // Cliente con/sin CUIT            
      usuario: "admin",
      id_usuario: 1,                              // debe ser dinamico con el tipo de usuario / admin=1, cajero=2, etc
      metodo_pago: metodoPago.toUpperCase(),
      total_venta: totalVenta,
      /* FALTA AGREGAR CUIT */
      /* paga_con: metodoPago === "efectivo" ? montoPagado : undefined, */  // probar si anda CON esto
      quiere_factura: true,
      tipo_comprobante_solicitado: (() => {
        switch (tipoFacturacion) {
          case "factura":
            return "Factura";
          case "comprobante":
            return "Comprobante";
          case "remito":
            return "Remito";
          case "presupuesto":
            return "Presupuesto";
          default:
            return "Desconocido";
        }
      })(),
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

  return (            

    <form onSubmit={handleSubmit} 
    className="flex flex-col w-full lg:w-1/2 rounded-xl bg-white shadow-md">

      {/* Header del Cajero */}
      <div className="w-full flex flex-row justify-between items-center p-6 bg-green-700 rounded-t-xl">
        <h4 className="text-2xl font-semibold text-white">Cajero</h4>
        <p className="text-2xl font-semibold text-white md:hidden">${totalVenta}</p>
      </div>

      {/* Cajero */}
      <div className="flex flex-col justify-between w-full gap-6 p-8">

        {/* Tipo Cliente */}
        <div className="flex flex-col md:flex-row w-full gap-4 justify-between items-center">
          <Label className="text-2xl font-semibold text-green-900 w-full md:max-w-1/4">Tipo de Cliente</Label>
          <div className="flex flex-col gap-2 w-full md:w-2/3">
            <Select
              defaultValue={tipoClienteSeleccionado.id}
              onValueChange={(value) => {
                const cliente = tipoCliente.find(p => p.id === value);
                if (cliente) setTipoClienteSeleccionado(cliente);
              }}
            >
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

            {/* Si es Cliente Final, input para registrar su CUIT */}
            {tipoClienteSeleccionado.id === "0" && (         
              <Input
                type="text"
                placeholder="Ingresar CUIT del cliente - sin espacios ni puntos"
                value={cuitManual}
                onChange={(e) => setCuitManual(e.target.value)}
                className="mt-1 text-black w-full"
              />
            )}

            {/* Si el tipo de cliente es con CUIT... */}
            {tipoClienteSeleccionado.id === "1" || tipoClienteSeleccionado.id === "2" ? (
            <div className="w-full flex flex-col gap-2">
              {!clientes.length ? (
                <p className="text-green-900 font-semibold">Cargando clientes...</p>
              ) : (
                <Popover open={openCliente} onOpenChange={setOpenCliente}>
                  <PopoverTrigger asChild>
                    <button
                      role="combobox"
                      aria-controls="clientes-list"
                      aria-expanded={openCliente}
                      className="w-full justify-between text-left cursor-pointer border px-3 py-2 rounded-md shadow-sm bg-white text-black flex items-center"
                    >
                      {clienteSeleccionado
                        ? `${clienteSeleccionado.nombre_razon_social} (${clienteSeleccionado.cuit || "Sin CUIT"})`
                        : "Seleccionar cliente"}
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
                      <CommandInput placeholder="Buscar cliente por nombre..." />
                      <CommandEmpty>No se encontró ningún cliente.</CommandEmpty>
                      <CommandGroup>
                        {clientes
                          .filter((cliente) => {
                            // Filtrado según tipo de cliente seleccionado
                            if (tipoClienteSeleccionado.id === "1") return !!cliente.cuit;
                            if (tipoClienteSeleccionado.id === "2") return !cliente.cuit;
                            return false;
                          })
                          .map((cliente) => (
                            <CommandItem
                              key={cliente.id}
                              value={cliente.nombre_razon_social}
                              className="pl-2 pr-4 py-2 text-sm text-black cursor-pointer"
                              onSelect={() => {
                                setClienteSeleccionado(cliente);
                                setOpenCliente(false);
                              }}
                            >
                              <span className="truncate">
                                {cliente.nombre_razon_social} ({cliente.cuit || "Sin CUIT"})
                              </span>
                            </CommandItem>
                          ))}
                      </CommandGroup>
                    </Command>
                  </PopoverContent>
                </Popover>
              )}
            </div>
          ) : null}
          </div>
        </div>
        <span className="block w-full h-0.5 bg-green-900"></span>

        {/* Dropdown de Productos */}
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
                            {p.nombre} | ${tipoClienteSeleccionado.id === "1" ? p.venta_negocio : p.precio_venta} | Stock: {p.stock_actual}
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

        {/* Seleccionar cantidad de un Producto - limitada por Stock*/}
        <div className="flex flex-col gap-4 items-start justify-between md:flex-row">
          <Label className="text-2xl font-semibold text-green-900">Cantidad</Label>
          <Input
            type="number"
            min={1}
            max={productoSeleccionado?.stock_actual || 9999}
            value={cantidad === 0 ? "" : cantidad}
            onChange={(e) => {
              const input = e.target.value;

              // Permitir input vacío
              if (input === "") {
                setCantidad(0);
                return;
              }

              // Convertimos a numero
              const parsed = parseInt(input, 10);
              // Ignorar si no es número válido
              if (isNaN(parsed)) return;

              // Limitar al stock
              const max = productoSeleccionado?.stock_actual ?? Infinity;
              setCantidad(Math.min(parsed, max));
            }}
            className="w-full md:max-w-2/3 text-black"
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
          className="!py-6"
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
                  value={montoPagado === 0 ? "" : montoPagado}
                  onChange={(e) => {
                    const input = e.target.value;
                    if (input === "") {
                      setMontoPagado(0);
                      return;
                    }
                    const parsed = parseInt(input, 10);
                    if (isNaN(parsed)) return;
                    setMontoPagado(parsed);
                  }}
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


        {/* Opciones de Tipo de Facturación */}
        <RadioGroup
          value={tipoFacturacion}
          onValueChange={setTipoFacturacion}
          className="flex flex-col gap-4 md:flex-row flex-wrap"
        >
          {/* Factura */}
          <Label
            htmlFor="factura"
            className="flex flex-row items-center w-full md:w-[48%] lg:flex-row cursor-pointer text-black border-green-900 hover:bg-green-400 dark:hover:bg-green-700 gap-3 rounded-lg border p-3 transition-colors duration-200 data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900"
          >
            <RadioGroupItem
              value="factura"
              id="factura"
              className="data-[state=checked]:border-white data-[state=checked]:bg-white"
            />
            <span className="text-sm leading-none font-medium">Factura</span>
          </Label>

          {/* Comprobante */}
          <Label
            htmlFor="comprobante"
            className="flex flex-row items-center w-full md:w-[48%] lg:flex-row cursor-pointer text-black border-green-900 hover:bg-green-400 dark:hover:bg-green-700 gap-3 rounded-lg border p-3 transition-colors duration-200 data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900"
          >
            <RadioGroupItem
              value="comprobante"
              id="comprobante"
              className="data-[state=checked]:border-white data-[state=checked]:bg-white"
            />
            <span className="text-sm leading-none font-medium">Comprobante</span>
          </Label>

          {/* Remito y Presupuesto */}
          <TooltipProvider>
            <div className="flex flex-wrap gap-4 w-full">
              {/* Remito - con mensaje informativo */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Label
                    htmlFor="remito"
                    className={`flex flex-row items-center w-full md:w-[48%] lg:flex-row text-black border-green-900 gap-3 rounded-lg border p-3 transition-colors duration-200
                      ${!habilitarExtras
                        ? "opacity-50 cursor-not-allowed"
                        : "cursor-pointer hover:bg-green-400 dark:hover:bg-green-700"}
                      data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900`}
                  >
                    <RadioGroupItem
                      value="remito"
                      id="remito"
                      disabled={!habilitarExtras}
                      className="data-[state=checked]:border-white data-[state=checked]:bg-white"
                    />
                    <span className="text-sm leading-none font-medium">Remito</span>
                  </Label>
                </TooltipTrigger>
                {!habilitarExtras && (
                  <TooltipContent>
                    <p>Contactá al administrador para habilitar esta opción</p>
                  </TooltipContent>
                )}
              </Tooltip>

              {/* Presupuesto - - con mensaje informativo */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Label
                    htmlFor="presupuesto"
                    className={`flex flex-row items-center w-full md:w-[48%] lg:flex-row text-black border-green-900 gap-3 rounded-lg border p-3 transition-colors duration-200
                      ${!habilitarExtras
                        ? "opacity-50 cursor-not-allowed"
                        : "cursor-pointer hover:bg-green-400 dark:hover:bg-green-700"}
                      data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900`}
                  >
                    <RadioGroupItem
                      value="presupuesto"
                      id="presupuesto"
                      disabled={!habilitarExtras}
                      className="data-[state=checked]:border-white data-[state=checked]:bg-white"
                    />
                    <span className="text-sm leading-none font-medium">Presupuesto</span>
                  </Label>
                </TooltipTrigger>
                {!habilitarExtras && (
                  <TooltipContent>
                    <p>Contactá al administrador para habilitar esta opción</p>
                  </TooltipContent>
                )}
              </Tooltip>
            </div>
          </TooltipProvider>

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
        <div className="flex flex-col sm:flex-row gap-4 justify-between items-center px-2">
          <Label className="text-2xl font-semibold text-green-900">Total del Pedido</Label>
          <p className="text-3xl font-semibold text-green-900">${totalVenta}</p>
        </div>

        {/* Botón Final: Registra venta y envia toda la info al server */}
        <Button
          type="submit"
          disabled={isLoading}
          className={`!py-6 bg-green-900 flex items-center justify-center gap-2 "
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