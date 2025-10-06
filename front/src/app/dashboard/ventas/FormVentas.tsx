"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue
} from "@/components/ui/select"

// Stores
import { useFacturacionStore } from "@/lib/facturacionStore";
import { useAuthStore } from "@/lib/authStore"
import { useEmpresaStore } from '@/lib/empresaStore';
import { useProductoStore } from "@/lib/productoStore";

// --- Componentes Hijos ---
import { SeccionCliente } from "./SeccionCliente";
import { SeccionProducto } from "./SeccionProducto";
import { SeccionCantidad } from "./SeccionCantidad";
import { Accordion, AccordionItem } from "@/components/ui/accordion"
import { AccordionContent, AccordionTrigger } from "@/components/ui/accordion"

// --- Interfaces y Tipos ---
interface ItemComprobante {
  descripcion: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
  tasa_iva: number;
  descuento_especifico?: number;
  descuento_especifico_por?: number;
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

// Tipo para el producto que se selecciona del dropdown
type ProductoSeleccionado = {
  id: string;
  nombre: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
  unidad_venta: string;
};

// --- Constantes ---
const tipoCliente = [
  { id: "0", nombre: "Cliente Final" },
  { id: "1", nombre: "Cliente Registrado" },
];

// --- Props del Componente ---
interface FormVentasProps {
  onAgregarProducto: (prod: {
    tipo: string;
    cantidad: number;
    precioTotal: number;
    descuentoAplicado: boolean;
    porcentajeDescuento: number;

    descuentoNominal: number;
  }) => void;
  totalVenta: number;
  productosVendidos: {
    tipo: string;
    cantidad: number;
    precioTotal: number;
    descuentoAplicado?: boolean;
    porcentajeDescuento?: number;
    descuentoNominal?: number;
  }[];
  onLimpiarResumen: () => void;
  // Props para mover la lógica del total al padre
  descuentoSobreTotal: number;
  setDescuentoSobreTotal: (value: number) => void;
  descuentoNominalTotal: number;
  setDescuentoNominalTotal: (value: number) => void;
  metodoPago: string;
  setMetodoPago: (value: string) => void;
  totalVentaFinal: number;
  vuelto: number;
  montoPagado: number;
  setMontoPagado: (value: number) => void;
}


// --- Componente Principal ---
function FormVentas({
  onAgregarProducto,
  totalVenta,
  productosVendidos,
  onLimpiarResumen,
  descuentoSobreTotal,
  setDescuentoSobreTotal,
  descuentoNominalTotal,
  setDescuentoNominalTotal,
  metodoPago,
  setMetodoPago,
  totalVentaFinal,
  vuelto,
  montoPagado,
  setMontoPagado,
}: FormVentasProps) {

  /* Estados */
  const productos = useProductoStore((state) => state.productos);
  const setProductos = useProductoStore((state) => state.setProductos);
  const [productoSeleccionado, setProductoSeleccionado] = useState<ProductoSeleccionado | null>(null);
  const token = useAuthStore((state) => state.token);
  const { formatoComprobante } = useFacturacionStore();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [clienteSeleccionado, setClienteSeleccionado] = useState<Cliente | null>(null);
  const [openCliente, setOpenCliente] = useState(false);
  const [busquedaCliente, setBusquedaCliente] = useState("");
  const [cuitManual, setCuitManual] = useState("");
  const [cantidad, setCantidad] = useState(1); // Representa la cantidad final a agregar
  const [descuentoPorcentual, setDescuentoPorcentual] = useState(0);
  const [descuentoNominal, setDescuentoNominal] = useState(0);
  const [open, setOpen] = useState(false);
  const [tipoClienteSeleccionado, setTipoClienteSeleccionado] = useState(tipoCliente[0]);
  const [inputEfectivo, setInputEfectivo] = useState("");
  const [pagoDividido, setPagoDividido] = useState(false);
  const [detallePagoDividido, setDetallePagoDividido] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { habilitarExtras } = useFacturacionStore();
  const [tipoFacturacion, setTipoFacturacion] = useState("factura");
  const [codigo, setCodigoEscaneado] = useState("");
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [productoEscaneado, setProductoEscaneado] = useState<ProductoSeleccionado | null>(null);
  const [cantidadEscaneada, setCantidadEscaneada] = useState(1);
  const inputRef = useRef<HTMLInputElement>(null);
  const cantidadInputRef = useRef<HTMLInputElement>(null);
  const empresa = useEmpresaStore((state) => state.empresa);
  const [checkoutVisible, setCheckoutVisible] = useState(false);
  const checkoutSectionRef = useRef<HTMLDivElement>(null);


  // Estados para Venta a Granel
  const [modoVenta, setModoVenta] = useState<'unidad' | 'granel'>('unidad');
  const [inputCantidadGranel, setInputCantidadGranel] = useState("1");
  const [inputPrecioGranel, setInputPrecioGranel] = useState("");

  /* Lógica y Hooks */
  const getPrecioProducto = useCallback((producto: ProductoSeleccionado | null): number => {
    if (!producto) return 0;
    if (tipoClienteSeleccionado.id === "0") return producto.precio_venta;
    return producto.venta_negocio;
  }, [tipoClienteSeleccionado]);


  const totalProducto = productoSeleccionado ? getPrecioProducto(productoSeleccionado) * cantidad : 0;
  const subtotal = totalProducto * (1 - descuentoPorcentual / 100);
  const productoConDescuento = Math.max(0, subtotal - descuentoNominal);

  // Hook para cambiar el modo de venta según el producto seleccionado
  useEffect(() => {
    if (productoSeleccionado) {
      const esVentaPorUnidad = !productoSeleccionado.unidad_venta || productoSeleccionado.unidad_venta.toLowerCase() === 'unidad';
      if (!esVentaPorUnidad) {
        setModoVenta('granel');
        const precioUnitario = getPrecioProducto(productoSeleccionado);
        setInputCantidadGranel("1");
        setInputPrecioGranel(precioUnitario.toFixed(2));
        setCantidad(1);
      } else {
        setModoVenta('unidad');
        setCantidad(1);
      }
    } else {
      setModoVenta('unidad');
    }
  }, [productoSeleccionado, tipoClienteSeleccionado, getPrecioProducto]);

  // Handlers para los inputs de venta a granel
  const handleCantidadGranelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const nuevoValor = e.target.value;
    setInputCantidadGranel(nuevoValor);
    if (productoSeleccionado) {
      const cantidadNum = parseFloat(nuevoValor) || 0;
      const precioUnitario = getPrecioProducto(productoSeleccionado);
      setInputPrecioGranel((cantidadNum * precioUnitario).toFixed(2));
      setCantidad(cantidadNum);
    }
  };

  const handlePrecioGranelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const nuevoValor = e.target.value;
    setInputPrecioGranel(nuevoValor);
    if (productoSeleccionado && getPrecioProducto(productoSeleccionado) > 0) {
      const precioNum = parseFloat(nuevoValor) || 0;
      const precioUnitario = getPrecioProducto(productoSeleccionado);
      const cantidadCalculada = (precioNum / precioUnitario).toFixed(3);
      setInputCantidadGranel(cantidadCalculada);
      setCantidad(parseFloat(cantidadCalculada));
    }
  };

  const handleAgregarProducto = () => {
    if (!productoSeleccionado || cantidad <= 0) {
      toast.error("Seleccione un producto y una cantidad válida.");
      return;
    };
    onAgregarProducto({
      tipo: productoSeleccionado.nombre,
      cantidad,
      precioTotal: productoConDescuento,
      descuentoAplicado: descuentoPorcentual > 0 || descuentoNominal > 0,
      porcentajeDescuento: descuentoPorcentual, // Asignación explícita
      descuentoNominal: descuentoNominal
    });
    setProductoSeleccionado(null);
    setCantidad(1);
    setDescuentoNominal(0);
    setDescuentoPorcentual(0);
    setModoVenta('unidad');
    inputRef.current?.focus();
    toast.success("Producto agregado al resumen.");
  };

  const resetFormularioVenta = () => {
    onLimpiarResumen();
    setMetodoPago("efectivo");
    setMontoPagado(0);
    setPagoDividido(false);
    setDetallePagoDividido("");
    setTipoFacturacion("factura");
    setClienteSeleccionado(null);
    setTipoClienteSeleccionado(tipoCliente[0]);
    setBusquedaCliente("");
    setOpenCliente(false);
    setCuitManual("");
    setDescuentoNominalTotal(0);
    setDescuentoSobreTotal(0);
    setDescuentoPorcentual(0);
    setDescuentoNominal(0);
    setObservaciones("");
    setCantidad(1);
    setInputEfectivo("");
    setOpen(false);
    setCodigoEscaneado("");
    setProductoSeleccionado(null);
    setModoVenta('unidad');
    setCheckoutVisible(false); // <-- Ocultar la sección de checkout al resetear
  };

  const formatearMoneda = (valor: string): string => {
    const limpio = valor.replace(/[^\d]/g, "");
    if (!limpio) return "";
    const conPuntos = parseInt(limpio).toLocaleString("es-AR");
    return `$${conPuntos}`;
  }

  const limpiarMoneda = (valor: string): number => {
    if (!valor) return 0;
    const limpio = valor
      .replace(/\./g, "")
      .replace(",", ".")
      .replace(/[^\d.]/g, "");
    return parseFloat(limpio) || 0;
  }

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (!codigo) return;

      try {
        const res = await fetch(`https://sistema-ima.sistemataup.online/api/articulos/codigos/buscar/${codigo}`, {
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        });

        if (!res.ok) {
          throw new Error('Producto no encontrado');
        }

        const data = await res.json();

        const productoAdaptado: ProductoSeleccionado = {
          id: data.id.toString(),
          nombre: data.descripcion || "Producto sin nombre",
          precio_venta: data.precio_venta,
          venta_negocio: data.venta_negocio,
          stock_actual: data.stock_actual,
          unidad_venta: data.unidad_venta || 'Unidad'
        };

        setProductoEscaneado(productoAdaptado);
        setCantidadEscaneada(1);
        setPopoverOpen(true);
        setCodigoEscaneado('');

      } catch (error) {
        console.error(error);
        toast.error(error instanceof Error ? error.message : `Producto no encontrado: ${codigo}`);
        setCodigoEscaneado('');
        inputRef.current?.focus();
      }
    }
  };

  const handleAgregarDesdePopover = () => {
    if (!productoEscaneado || cantidadEscaneada <= 0) {
      return;
    }

    onAgregarProducto({
      tipo: productoEscaneado.nombre,
      cantidad: cantidadEscaneada,
      precioTotal: productoEscaneado.precio_venta * cantidadEscaneada,
      descuentoAplicado: false,
      porcentajeDescuento: 0,
      descuentoNominal: 0
    });

    setPopoverOpen(false);
    setCodigoEscaneado('');
    setProductoEscaneado(null);
    inputRef.current?.focus();
    toast.success(`'${productoEscaneado.nombre}' x${cantidadEscaneada} agregado.`);
  };

  // Efecto de Scroll al abrir la seccion de metodos de pago
  useEffect(() => {
    // Si la sección de checkout se hizo visible y la referencia al elemento existe...
    if (checkoutVisible && checkoutSectionRef.current) {
      // ...hacemos un scroll suave hasta ese elemento.
      checkoutSectionRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  }, [checkoutVisible]); // Este efecto se ejecuta cada vez que 'checkoutVisible' cambia.

  useEffect(() => {
    const fetchClientes = async () => {
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/clientes/obtener-todos", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const data: Cliente[] = await res.json();
        const clientesActivos = data.filter((cliente: Cliente) => cliente.activo);
        setClientes(clientesActivos);
      } catch (error) {
        console.error("❌ Error al obtener clientes:", error);
      }
    };
    fetchClientes();
  }, [token]);

  // Funcion que refresca el stock en el store despues de cada venta
  const refrescarProductos = async () => {
    // Usamos el token que ya tienes disponible en el componente
    if (!token) {
      console.error("No hay token para refrescar productos.");
      return;
    }

    try {
      console.log("🔄 Refrescando catálogo de productos...");
      const res = await fetch("https://sistema-ima.sistemataup.online/api/articulos/obtener_todos", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        throw new Error("Error al refrescar productos desde el servidor");
      }

      // Reutilizamos el tipado que definiste en el login
      type ProductoAPI = {
        id: number | string;
        nombre?: string;
        descripcion?: string;
        precio_venta: number;
        venta_negocio: number;
        stock_actual: number;
        unidad_venta: string;
      };

      const data: ProductoAPI[] = await res.json();
      const adaptados = data.map((p) => ({
        id: String(p.id),
        nombre: p.nombre ?? p.descripcion ?? "",
        precio_venta: p.precio_venta,
        venta_negocio: p.venta_negocio,
        stock_actual: p.stock_actual,
        unidad_venta: p.unidad_venta || 'Unidad',
      }));

      // Usamos la acción del store para actualizar el estado global
      setProductos(adaptados);
      // Opcional: También puedes actualizar el localStorage si lo necesitas síncrono
      localStorage.setItem("productos", JSON.stringify(adaptados));

      console.log("✅ Catálogo de productos actualizado.");

    } catch (err) {
      // Usamos un toast para notificar el error de forma no invasiva
      toast.error("No se pudo actualizar el stock de productos en tiempo real.");
      console.error("Error actualizando productos post-venta:", err);
    }
  };

  // POST - Venta, Genera Comprobante y Actualiza Stock en cada una
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    if (productosVendidos.length === 0) {
      toast.error("❌ No hay productos cargados en la venta.");
      setIsLoading(false);
      return;
    }

    if (metodoPago === "efectivo" && montoPagado < totalVentaFinal) {
      toast.error("❌ El monto abonado no puede ser menor al valor final del pedido.");
      setIsLoading(false);
      return;
    }

    if (tipoClienteSeleccionado.id === "1" && !clienteSeleccionado) {
      toast.error("❌ Debe seleccionar un cliente registrado.");
      setIsLoading(false);
      return;
    }

    if (tipoClienteSeleccionado.id === "0" && totalVenta > 200000) {
      if (cuitManual.trim() === "") {
        toast.error("❌ Para montos mayores a $200.000, debe ingresar un CUIT.");
        setIsLoading(false);
        return;
      }
      if (!/^\d{11}$/.test(cuitManual.trim())) {
        toast.error("❌ El CUIT ingresado no es válido. Debe tener 11 dígitos.");
        setIsLoading(false);
        return;
      }
    }

    // Determinar un tipo_comprobante_solicitado más específico
    let tipoSolicitadoPayload = tipoFacturacion.toLowerCase();
    // Si es factura y hay información de CUIT (cliente registrado o cuit manual), intentar especificar A/B
    const cuitReceptor = tipoClienteSeleccionado.id === "0" ? (cuitManual || "0") : (clienteSeleccionado?.cuit || clienteSeleccionado?.identificacion_fiscal || "0");
    if (tipoFacturacion === "factura") {
      if (cuitReceptor && cuitReceptor.toString().length === 11) {
        tipoSolicitadoPayload = "factura_a";
      } else {
        tipoSolicitadoPayload = "factura_b";
      }
    }

    const ventaPayload = {
      id_cliente: tipoClienteSeleccionado.id === "0" ? 0 : clienteSeleccionado?.id ?? 0,
      metodo_pago: metodoPago.toUpperCase(),
      total_venta: totalVenta,
      paga_con: montoPagado,
      pago_separado: pagoDividido,
      detalles_pago_separado: detallePagoDividido,
      tipo_comprobante_solicitado: tipoSolicitadoPayload,
      quiere_factura: tipoFacturacion === "factura",
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
      if (!empresa || !empresa.id_empresa) {
        toast.error("No se pudieron cargar los datos de la empresa. No se puede realizar la venta.");
        setIsLoading(false);
        return;
      }

      const response = await fetch("https://sistema-ima.sistemataup.online/api/caja/ventas/registrar", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(ventaPayload)
      });

      if (!response.ok) {
        const error = await response.json();
        toast.error(`❌ Error al registrar venta: ${error.detail || response.statusText}`);
        setIsLoading(false);
        return;
      }

      const data = await response.json();
      toast.success(`✅ Venta registrada: ${data.message}`);

      // Actualizamos el Store despues de cada venta..
      await refrescarProductos();

      // Funcion que genera el comprobante
      const generarComprobante = async () => {
        try {
          const itemsBase = productosVendidos.map((p): ItemComprobante => {
            const productoReal = productos.find((prod) => prod.nombre === p.tipo);
            const item: ItemComprobante = {
              descripcion: productoReal?.nombre || p.tipo,
              cantidad: p.cantidad,
              precio_unitario: productoReal ? getPrecioProducto(productoReal) : 0,
              subtotal: p.precioTotal,
              tasa_iva: 21
            };
            if (tipoFacturacion !== "factura") {
              item.descuento_especifico = p.descuentoNominal || 0;
              item.descuento_especifico_por = p.porcentajeDescuento || 0;
            }
            return item;
          });

          const transaccion = tipoFacturacion === "factura"
            ? { items: itemsBase, total: totalVentaFinal, observaciones: observaciones || "" }
            : { items: itemsBase, total: totalVentaFinal, descuento_general: descuentoNominalTotal || 0, descuento_general_por: descuentoSobreTotal || 0, observaciones: observaciones || "" };

          const reqPayload = {
            formato: formatoComprobante.toLowerCase(),
            tipo: tipoFacturacion.toLowerCase(),
            emisor: {
              cuit: empresa.cuit?.toString() || "0",
              razon_social: empresa.nombre_negocio || "N/A",
              domicilio: empresa.direccion_negocio || "N/A",
              punto_venta: empresa.afip_punto_venta_predeterminado || 1,
              condicion_iva: empresa.afip_condicion_iva || "Responsable Inscripto",
            },
            receptor: {
              nombre_razon_social: tipoClienteSeleccionado.id === "0" ? "Consumidor Final" : clienteSeleccionado?.nombre_razon_social ?? "N/A",
              cuit_o_dni: tipoClienteSeleccionado.id === "0" ? cuitManual || "0" : clienteSeleccionado?.cuit || clienteSeleccionado?.identificacion_fiscal || "0",
              domicilio: "Sin especificar",
              condicion_iva: tipoClienteSeleccionado.id === "0" ? "Consumidor Final" : clienteSeleccionado?.condicion_iva ?? "Consumidor Final"
            },
            transaccion
          };

          const respComp = await fetch("https://sistema-ima.sistemataup.online/api/comprobantes/generar", {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
            body: JSON.stringify(reqPayload)
          });

          if (!respComp.ok) {
            const errorComp = await respComp.json();
            toast.error(`❌ Error al generar comprobante: ${errorComp.detail}`);
            return;
          }

          const blob = await respComp.blob();
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = `${tipoFacturacion}-${Date.now()}.pdf`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
          toast.success("✅ Comprobante generado correctamente.");

        } catch (error) {
          console.error("❌ Error en la generación del comprobante:", error);
          toast.error("❌ Fallo al intentar generar el comprobante.");
        }
      };

      await generarComprobante();

      resetFormularioVenta();
      window.scrollTo({ top: 0, behavior: "smooth" });

    } catch (error) {
      console.error("Detalles del error de registro:", error);
      toast.error("❌ Error de red al registrar la venta.");
    } finally {
      setIsLoading(false);
    }
  };


  /* Renderizado del Componente */
  return (
    <form onSubmit={handleSubmit} className="flex flex-col w-full lg:w-1/2 rounded-xl bg-white shadow-md">

      {/* Header del Form */}
      <div className="w-full flex flex-row justify-between items-center px-6 py-4 bg-green-700 rounded-t-xl">
        <h4 className="text-xl font-semibold text-white">Cajero</h4>
        <p className="text-xl font-semibold text-white md:hidden">${totalVenta.toFixed(2)}</p>
      </div>

      {/* Cuerpo del Form */}
      <div className="flex flex-col justify-between w-full gap-6 p-8">

        {/* Desplegable */}
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="item-1">
            <AccordionTrigger className="cursor-pointer text-md">Configuración de Cliente y Descuentos</AccordionTrigger>
            <AccordionContent className="flex flex-col gap-4">
              <SeccionCliente
                tipoClienteSeleccionado={tipoClienteSeleccionado}
                setTipoClienteSeleccionado={setTipoClienteSeleccionado}
                tiposDeCliente={tipoCliente}
                cuitManual={cuitManual}
                setCuitManual={setCuitManual}
                totalVenta={totalVenta}
                clientes={clientes}
                clienteSeleccionado={clienteSeleccionado}
                setClienteSeleccionado={setClienteSeleccionado}
                openCliente={openCliente}
                setOpenCliente={setOpenCliente}
                busquedaCliente={busquedaCliente}
                setBusquedaCliente={setBusquedaCliente}
              />
              <span className="block w-full h-0.5 bg-green-900"></span>
              <div className="flex flex-col gap-4 items-start justify-between md:flex-row md:items-center">
                <Label className="text-lg font-semibold text-green-900">Descuento por Producto (%)</Label>
                <Input
                  type="number"
                  onWheel={(e) => (e.target as HTMLInputElement).blur()}
                  min={0}
                  max={100}
                  value={descuentoPorcentual === 0 ? "" : descuentoPorcentual}
                  onChange={(e) => setDescuentoPorcentual(Math.min(parseInt(e.target.value, 10) || 0, 100))}
                  className="w-full md:max-w-2/3 text-black"
                />
              </div>

              <div className="flex flex-col gap-4 items-start justify-between md:flex-row md:items-center">
                <Label className="text-lg font-semibold text-green-900">Descuento por Producto ($)</Label>
                <Input
                  type="number"
                  onWheel={(e) => (e.target as HTMLInputElement).blur()}
                  min={0}
                  value={descuentoNominal === 0 ? "" : descuentoNominal}
                  onChange={(e) => setDescuentoNominal(Math.min(parseFloat(e.target.value) || 0, totalProducto))}
                  className="w-full md:max-w-2/3 text-black"
                />
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
        <span className="block w-full h-0.5 bg-green-900"></span>

        {/* --- CONTENEDOR GRID PARA PRODUCTO Y CANTIDAD --- */}
        <div className="flex flex-col gap-6">

          {/* Sección de Producto */}
          <SeccionProducto
            inputRef={inputRef}
            codigo={codigo}
            setCodigoEscaneado={setCodigoEscaneado}
            handleKeyDown={handleKeyDown}
            productos={productos}
            productoSeleccionado={productoSeleccionado}
            setProductoSeleccionado={setProductoSeleccionado}
            open={open}
            setOpen={setOpen}
            tipoClienteSeleccionadoId={tipoClienteSeleccionado.id}
            popoverOpen={popoverOpen}
            setPopoverOpen={setPopoverOpen}
            productoEscaneado={productoEscaneado}
            cantidadEscaneada={cantidadEscaneada}
            setCantidadEscaneada={setCantidadEscaneada}
            handleAgregarDesdePopover={handleAgregarDesdePopover}
          />

          {/* Sección de Cantidad */}
          <SeccionCantidad
            cantidadInputRef={cantidadInputRef}
            modoVenta={modoVenta}
            cantidadUnidad={cantidad}
            setCantidadUnidad={setCantidad}
            stockActual={productoSeleccionado?.stock_actual ?? 9999}
            unidadDeVenta={productoSeleccionado?.unidad_venta || ''}
            inputCantidadGranel={inputCantidadGranel}
            handleCantidadGranelChange={handleCantidadGranelChange}
            inputPrecioGranel={inputPrecioGranel}
            handlePrecioGranelChange={handlePrecioGranelChange}
          />
        </div>
        <span className="block w-full h-0.5 bg-green-900"></span>

        <div className="flex flex-col md:flex-row gap-4 justify-between items-center mt-4">
          <p className="text-xl font-semibold text-green-900">Total del Producto:</p>
          <p className="text-2xl font-bold text-green-900">${productoConDescuento.toFixed(2)}</p>
        </div>

        {/* Agrega producto al resumen */}
        <Button
          variant="success"
          className="!py-6 mt-2"
          type="button"
          onClick={handleAgregarProducto}
        >
          + Agregar producto
        </Button>

        <span className="block w-full h-0.5 bg-green-900"></span>

        {/* Sección para Finalizar compra */}
        <Button
          className="!py-6 !bg-emerald-800"
          type="button"
          onClick={() => setCheckoutVisible(!checkoutVisible)}
        >
          {checkoutVisible ? 'Ocultar Opciones de Pago' : 'Finalizar Compra'}
        </Button>

        {checkoutVisible && (
          <div ref={checkoutSectionRef} className="flex flex-col gap-6 mt-6 animate-in fade-in-0 duration-300">
            <div className="flex flex-col gap-4 mt-4">
              <div className="flex flex-col gap-4 items-start justify-between md:flex-row">
                <Label className="text-2xl font-semibold text-green-900">Método de Pago</Label>
                <Select value={metodoPago} onValueChange={setMetodoPago}>
                  <SelectTrigger className="w-full md:max-w-1/2 cursor-pointer text-black">
                    <SelectValue placeholder="Seleccionar método" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="efectivo">Efectivo</SelectItem>
                    <SelectItem value="transferencia">Transferencia</SelectItem>
                    <SelectItem value="bancario">POS</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {metodoPago === 'efectivo' && (
                <div className="flex flex-col gap-4 p-4 bg-green-800 rounded-lg mt-2">
                  <div className="flex flex-col md:flex-row gap-4 items-start justify-between">
                    <Label className="text-2xl font-semibold text-white">Costo del Pedido:</Label>
                    <Input type="text" value={`$${totalVentaFinal.toLocaleString('es-AR')}`} disabled className="w-full md:max-w-1/2 font-semibold text-white" />
                  </div>
                  <div className="flex flex-col md:flex-row gap-4 items-start justify-between">
                    <Label className="text-2xl font-semibold text-white">Con cuánto abona:</Label>
                    <Input
                      inputMode="numeric"
                      value={inputEfectivo}
                      onChange={(e) => {
                        const valorInput = e.target.value;
                        setInputEfectivo(formatearMoneda(valorInput));
                        setMontoPagado(limpiarMoneda(valorInput));
                      }}
                      className="w-full md:max-w-1/2 font-semibold text-white"
                    />
                  </div>
                  <div className="flex flex-col md:flex-row gap-4 items-start justify-between">
                    <Label className="text-2xl font-semibold text-white">Vuelto:</Label>
                    <Input type="text" value={`$${vuelto.toLocaleString('es-AR')}`} disabled className="w-full md:max-w-1/2 font-semibold text-white" />
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center">
              <Label htmlFor="pagoDividido" className="flex items-center gap-2 text-green-950 text-md font-medium cursor-pointer">
                <Input
                  id="pagoDividido"
                  type="checkbox"
                  checked={pagoDividido}
                  onChange={(e) => setPagoDividido(e.target.checked)}
                  className="h-5 w-5 text-green-700 border-gray-300 rounded focus:ring-green-600 cursor-pointer"
                />
                <span>¿Paga de dos o mas formas?</span>
              </Label>
            </div>
            <span className="block w-full h-0.5 bg-green-900"></span>

            <RadioGroup value={tipoFacturacion} onValueChange={setTipoFacturacion} className="flex flex-col gap-4 md:flex-row flex-wrap">
              <Label htmlFor="factura" className="flex flex-row items-center w-full md:w-[48%] lg:flex-row cursor-pointer text-black border-green-900 hover:bg-green-400 dark:hover:bg-green-700 gap-3 rounded-lg border p-3 transition-colors duration-200 data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900">
                <RadioGroupItem value="factura" id="factura" className="data-[state=checked]:border-white data-[state=checked]:bg-white" />
                <span className="text-sm leading-none font-medium">Factura</span>
              </Label>
              <Label htmlFor="comprobante" className="flex flex-row items-center w-full md:w-[48%] lg:flex-row cursor-pointer text-black border-green-900 hover:bg-green-400 dark:hover:bg-green-700 gap-3 rounded-lg border p-3 transition-colors duration-200 data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900">
                <RadioGroupItem value="recibo" id="comprobante" className="data-[state=checked]:border-white data-[state=checked]:bg-white" />
                <span className="text-sm leading-none font-medium">Comprobante</span>
              </Label>
              <TooltipProvider>
                <div className="flex flex-wrap gap-4 w-full">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Label htmlFor="remito" className={`flex flex-row items-center w-full md:w-[48%] lg:flex-row text-black border-green-900 gap-3 rounded-lg border p-3 transition-colors duration-200 ${!habilitarExtras ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:bg-green-400 dark:hover:bg-green-700"} data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900`}>
                        <RadioGroupItem value="remito" id="remito" disabled={!habilitarExtras} className="data-[state=checked]:border-white data-[state=checked]:bg-white" />
                        <span className="text-sm leading-none font-medium">Remito</span>
                      </Label>
                    </TooltipTrigger>
                    {!habilitarExtras && (<TooltipContent><p>Contactá al administrador</p></TooltipContent>)}
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Label htmlFor="presupuesto" className={`flex flex-row items-center w-full md:w-[48%] lg:flex-row text-black border-green-900 gap-3 rounded-lg border p-3 transition-colors duration-200 ${!habilitarExtras ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:bg-green-400 dark:hover:bg-green-700"} data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 dark:data-[state=checked]:border-blue-900 dark:data-[state=checked]:bg-blue-900`}>
                        <RadioGroupItem value="presupuesto" id="presupuesto" disabled={!habilitarExtras} className="data-[state=checked]:border-white data-[state=checked]:bg-white" />
                        <span className="text-sm leading-none font-medium">Presupuesto</span>
                      </Label>
                    </TooltipTrigger>
                    {!habilitarExtras && (<TooltipContent><p>Contactá al administrador</p></TooltipContent>)}
                  </Tooltip>
                </div>
              </TooltipProvider>
            </RadioGroup>

            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="item-1">
                <AccordionTrigger className="cursor-pointer text-md">Observaciones y Descuentos Globales</AccordionTrigger>
                <AccordionContent className="flex flex-col gap-4 pt-4">
                  <div className="flex flex-col w-full gap-2">
                    <Label className="text-green-900 text-xl" htmlFor="message-2">Observaciones</Label>
                    <Textarea placeholder="Observaciones de la venta..." id="message-2" value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
                  </div>
                  <span className="block w-full h-0.5 bg-green-900"></span>

                  <div className="flex flex-col gap-4 items-start justify-between md:flex-row md:items-center">
                    <Label className="text-lg font-semibold text-green-900">Descuento Sobre Total (%)</Label>
                    <Input type="number" min={0} max={100} value={descuentoSobreTotal === 0 ? "" : descuentoSobreTotal} onWheel={(e) => (e.target as HTMLInputElement).blur()} onChange={(e) => setDescuentoSobreTotal(Math.min(parseInt(e.target.value, 10) || 0, 100))} className="w-full md:max-w-2/3 text-black" />
                  </div>
                  <div className="flex flex-col gap-4 items-start justify-between md:flex-row md:items-center">
                    <Label className="text-lg font-semibold text-green-900">Descuento Sobre Total ($)</Label>
                    <Input type="number" min={0} value={descuentoNominalTotal === 0 ? "" : descuentoNominalTotal} onWheel={(e) => (e.target as HTMLInputElement).blur()} onChange={(e) => setDescuentoNominalTotal(Math.min(parseFloat(e.target.value) || 0, totalVenta))} className="w-full md:max-w-2/3 text-black" />
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>

            <Button type="submit" disabled={isLoading} className={`!py-6 bg-green-900 flex items-center justify-center gap-2 ${isLoading ? "cursor-not-allowed opacity-50" : "hover:bg-green-700 cursor-pointer"}`}>
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {isLoading ? "Registrando..." : "Registrar Venta"}
            </Button>
          </div>
        )}
      </div>
    </form>
  );
}

export default FormVentas;