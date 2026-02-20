"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Loader2, RefreshCw } from "lucide-react";
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
import { API_CONFIG } from "@/lib/api-config";
import { attachAutoScaleBridge } from "@/lib/scaleSerial";

// --- Componentes Hijos ---
import { SeccionCliente } from "./SeccionCliente";
import { SeccionProducto } from "./SeccionProducto";
import { SeccionCantidad } from "./SeccionCantidad";
import { PagoMultiple, type Pago } from "./PagoMultiple";
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
    id?: string;
    tipo: string;
    cantidad: number;
    precioTotal: number;
    precioBase: number;
    descuentoAplicado: boolean;
    porcentajeDescuento: number;

    descuentoNominal: number;
  }) => void;
  totalVenta: number;
  productosVendidos: {
    id?: string;
    tipo: string;
    cantidad: number;
    precioTotal: number;
    precioBase: number;
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
  const [persistirProducto, setPersistirProducto] = useState(false); // Nuevo estado para persistir producto
  const inputRef = useRef<HTMLInputElement>(null);
  const cantidadInputRef = useRef<HTMLInputElement>(null);
  const empresa = useEmpresaStore((state) => state.empresa);
  const [checkoutVisible, setCheckoutVisible] = useState(false);
  const checkoutSectionRef = useRef<HTMLDivElement>(null);
  const [autoSubmitFlag, setAutoSubmitFlag] = useState(false);
  const [balanzaRetry, setBalanzaRetry] = useState(0);
  const [catalogoResetTick, setCatalogoResetTick] = useState(0);

  // Estados para Auto-Sincronización de Catálogo
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);

  // Estados para Pagos Múltiples
  const [usarPagosMultiples, setUsarPagosMultiples] = useState(false);
  const [pagosMultiples, setPagosMultiples] = useState<Pago[]>([]);

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
  const subtotal = totalProducto;
  const productoConDescuento = subtotal;

  // Hook para cambiar el modo de venta según el producto seleccionado
  useEffect(() => {
    if (productoSeleccionado) {
      // ✅ Normalizar unidad_venta: limpiar spaces, lowercase
      const unidadRaw = productoSeleccionado.unidad_venta || '';
      const unidad = unidadRaw.toLowerCase().trim().replace(/\s+/g, '');

      console.log(`[DEBUG] Producto: ${productoSeleccionado.nombre}, unidad_venta RAW: "${unidadRaw}", normalizada: "${unidad}"`);

      // 🔹 Detección PRECISA:
      // Primero: detectar GRANEL (tiene prioridad, palabras explícitas)
      const esGranel = (
        unidad.includes('gramo') ||
        unidad.includes('kg') ||
        unidad.includes('litro') ||
        unidad.includes('litros') ||
        (unidad.includes('gm') && !unidad.includes('u')) ||
        (unidad === 'g') ||
        (unidad === 'ml') ||
        (unidad === 'l')
      );

      // Segundo: detectar si es UNIDAD explícita
      const esUnitadExplicita = (
        unidad === 'unidad' ||
        unidad === 'unidades' ||
        unidad.startsWith('un') ||
        unidad === 'unit' ||
        unidad === 'units' ||
        unidad === 'und' ||
        unidad === 'pza' ||
        unidad === 'pzas' ||
        unidad === 'pieza' ||
        unidad === 'piezas'
      );

      // Tercero: detectar si es vacío o "sin información" (asumir UNIDAD por defecto)
      const esVacio = (
        unidad === '' ||
        unidad.includes('sininformacion') ||
        unidad.includes('sin') ||
        unidad.includes('info')
      );

      // Lógica final: 
      // - Si es claramente GRANEL → GRANEL
      // - Si es UNIDAD explícita → UNIDAD
      // - Si es vacío/sin info → UNIDAD (default seguro)
      // - Cualquier otro caso → UNIDAD (default)
      const esVentaPorUnidad = !esGranel;

      console.log(`[DEBUG] esGranel: ${esGranel}, esUnitadExplicita: ${esUnitadExplicita}, esVacio: ${esVacio}, modo: ${esVentaPorUnidad ? 'UNIDAD' : 'GRANEL'}`);

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
      id: productoSeleccionado.id,
      tipo: productoSeleccionado.nombre,
      cantidad,
      precioTotal: productoConDescuento,
      precioBase: totalProducto,
      descuentoAplicado: false,
      porcentajeDescuento: 0,
      descuentoNominal: 0
    });
    // Reset de campos
    if (!persistirProducto) {
      setProductoSeleccionado(null);
      setCodigoEscaneado("");
    }
    setCantidad(1);
    setInputCantidadGranel("1");
    setInputPrecioGranel("");

    // Foco
    setTimeout(() => {
      if (persistirProducto) {
        if (cantidadInputRef.current) cantidadInputRef.current.focus();
      } else {
        if (inputRef.current) inputRef.current.focus();
      }
    }, 100);
    toast.success("Producto agregado al resumen.");
  };

  const resetFormularioVenta = useCallback(() => {
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
    setObservaciones("");
    setCantidad(1);
    setInputEfectivo("");
    setOpen(false);
    setCodigoEscaneado("");
    setUsarPagosMultiples(false);
    setPagosMultiples([]);
    // Solo reseteamos el producto si no está activa la persistencia
    if (!persistirProducto) {
      setProductoSeleccionado(null);
    }
    setModoVenta('unidad');
    setCheckoutVisible(false); // <-- Ocultar la sección de checkout al resetear

    // Foco post-venta
    setTimeout(() => {
      if (persistirProducto) {
        if (cantidadInputRef.current) cantidadInputRef.current.focus();
      } else {
        if (inputRef.current) inputRef.current.focus();
      }
    }, 100);
  }, [onLimpiarResumen, persistirProducto]);

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
  }, [inputRef]);

  useEffect(() => {
    const cfg = empresa?.aclaraciones_legales ?? {};
    const autoAgregar = (cfg?.balanza_auto_agregar ?? "false") === "true";
    if (!autoAgregar) return;
    if (!token) return;
    let ctrl: { stop: () => Promise<void> } | null = null;
    (async () => {
      console.log("⚖️ [FormVentas] Iniciando conexión con balanza (Intento " + balanzaRetry + ")");
      ctrl = await attachAutoScaleBridge(token);
    })();
    return () => {
      if (ctrl) ctrl.stop();
    };
  }, [empresa, token, balanzaRetry]);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}/scanner/evento/poll`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) return;
        const payload = await res.json();
        if (!payload?.has_event) return;
        const ev = payload.event as { codigo?: string; id_articulo?: number; nombre?: string; precio?: number; peso?: number };
        if (ev.id_articulo) {
          const p = productos.find(pp => pp.id === String(ev.id_articulo));
          if (p) {
            const pUnit = typeof ev.precio === 'number' ? ev.precio : (tipoClienteSeleccionado.id === '0' ? p.precio_venta : p.venta_negocio);
            const cantidadEv = typeof ev.peso === 'number' ? ev.peso : 1;
            onAgregarProducto({
              tipo: p.nombre,
              cantidad: cantidadEv,
              precioTotal: pUnit * cantidadEv,
              precioBase: pUnit * cantidadEv,
              descuentoAplicado: false,
              porcentajeDescuento: 0,
              descuentoNominal: 0
            });
            toast.success(`Se agregó '${p.nombre}' desde escáner`);
            return;
          }
        }
        const cfg = empresa?.aclaraciones_legales ?? {};
        const autoAgregar = (cfg?.balanza_auto_agregar ?? "false") === "true";
        const autoFacturar = (cfg?.balanza_auto_facturar ?? "false") === "true";
        const precioFuente = (cfg?.balanza_precio_fuente ?? "producto") as 'producto' | 'evento';
        const balanzaId = cfg?.balanza_articulo_id ?? "";
        if (autoAgregar && typeof ev.peso === 'number') {
          if (balanzaId) {
            const p = productos.find(pp => pp.id === String(balanzaId));
            if (p) {
              const pUnit = precioFuente === 'evento' && typeof ev.precio === 'number'
                ? ev.precio
                : (tipoClienteSeleccionado.id === '0' ? p.precio_venta : p.venta_negocio);
              const cantidadEv = ev.peso;
              onAgregarProducto({
                tipo: p.nombre,
                cantidad: cantidadEv,
                precioTotal: pUnit * cantidadEv,
                precioBase: pUnit * cantidadEv,
                descuentoAplicado: false,
                porcentajeDescuento: 0,
                descuentoNominal: 0
              });
              toast.success(`Se agregó '${p.nombre}' desde balanza`);
              // Auto-facturación desactivada - usuario debe hacer click en Registrar
              return;
            }
          }
          if (typeof ev.precio === 'number') {
            const nombre = ev.nombre || 'Producto escáner';
            const cantidadEv = ev.peso;
            const precioTotalEv = ev.precio * cantidadEv;
            onAgregarProducto({
              tipo: nombre,
              cantidad: cantidadEv,
              precioTotal: precioTotalEv,
              precioBase: precioTotalEv,
              descuentoAplicado: false,
              porcentajeDescuento: 0,
              descuentoNominal: 0
            });
            toast.success(`Se agregó '${nombre}' desde escáner`);
            // Auto-facturación desactivada - usuario debe hacer click en Registrar
          }
        }
      } catch { }
    }, 1000);
    return () => clearInterval(interval);
  }, [token, productos, productoSeleccionado, getPrecioProducto, onAgregarProducto, empresa?.aclaraciones_legales, setMetodoPago, setMontoPagado, tipoClienteSeleccionado?.id, totalVentaFinal]);

  // Efecto para auto-enviar cuando viene desde balanza/escáner
  // Se posiciona después de la definición de handleSubmit para evitar uso antes de declaración

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Esta función solo se ejecuta cuando viene del escáner automático (código de barras)
    // No se ejecuta cuando el usuario está escribiendo manualmente gracias al control en SeccionProducto
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

        const precioUnitario =
          tipoClienteSeleccionado.id === "0"
            ? productoAdaptado.precio_venta
            : productoAdaptado.venta_negocio;

        onAgregarProducto({
          tipo: productoAdaptado.nombre,
          cantidad: 1,
          precioTotal: precioUnitario * 1,
          precioBase: precioUnitario * 1,
          descuentoAplicado: false,
          porcentajeDescuento: 0,
          descuentoNominal: 0
        });

        setCodigoEscaneado('');
        inputRef.current?.focus();
        toast.success("Producto agregado automáticamente");

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
      precioBase: productoEscaneado.precio_venta * cantidadEscaneada,
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


  // Función que refresca el stock en el store después de cada venta
  const refrescarProductos = useCallback(async () => {
    // Usamos el token que ya tienes disponible en el componente
    if (!token) {
      console.error("No hay token para refrescar productos.");
      return;
    }

    try {
      setIsSyncing(true);
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

      // Registrar el timestamp de última sincronización
      setLastSyncTime(new Date());

      console.log("✅ Catálogo de productos actualizado.");

    } catch (err) {
      // Usamos un toast para notificar el error de forma no invasiva
      toast.error("No se pudo actualizar el stock de productos en tiempo real.");
      console.error("Error actualizando productos post-venta:", err);
    } finally {
      setIsSyncing(false);
    }
  }, [token, setProductos]);

  useEffect(() => {
    const interval = setInterval(() => {
      refrescarProductos();
    }, 10000); // Refrescar cada 10 segundos
    return () => clearInterval(interval);
  }, [refrescarProductos]);

  useEffect(() => {
    let lastVersion = parseInt(localStorage.getItem("catalogo_version") || "0", 10);
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}/articulos/version`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) return;
        const data = await res.json() as { version?: number };
        const v = typeof data.version === "number" ? data.version : 0;
        if (v > lastVersion) {
          await refrescarProductos();
          lastVersion = v;
          localStorage.setItem("catalogo_version", String(v));
          toast.success("Catálogo actualizado");
        }
      } catch { }
    }, 5000);
    return () => clearInterval(interval);
  }, [token, refrescarProductos, catalogoResetTick]);

  useEffect(() => {
    const intervalMs = 300000;
    const interval = setInterval(async () => {
      try {
        localStorage.removeItem("producto-storage");
        localStorage.removeItem("productos");
        localStorage.setItem("catalogo_version", "0");
        setCatalogoResetTick((tick) => tick + 1);
        await refrescarProductos();
      } catch (err) {
        console.error("Error limpiando cache de productos:", err);
      }
    }, intervalMs);
    return () => clearInterval(interval);
  }, [refrescarProductos]);

  // Auto-sincronización cada 20 segundos para mantener catálogo actualizado
  useEffect(() => {
    const autoSyncInterval = setInterval(async () => {
      await refrescarProductos();
    }, 20000); // 20 segundos

    return () => clearInterval(autoSyncInterval);
  }, [refrescarProductos]);

  const imprimirComprobante = useCallback(async (
    tipo: string,
    items: ItemComprobante[],
    totalFinal: number,
    descGeneral: number,
    descGeneralPor: number,
    obs: string
  ) => {
    console.log(`[${new Date().toISOString()}] Iniciando impresión de ${tipo}`);

    const transaccion = tipo === "factura"
      ? { items, total: totalFinal, observaciones: obs }
      : { items, total: totalFinal, descuento_general: descGeneral, descuento_general_por: descGeneralPor, observaciones: obs };

    const aclaraciones: any = empresa?.aclaraciones_legales || {};
    const incluirTicketCambio = (aclaraciones.ticket_cambio_habilitado === "true" || aclaraciones.ticket_cambio_habilitado === true)
      && formatoComprobante.toLowerCase() !== "pdf";
    const plazoCambio = aclaraciones.ticket_cambio_plazo || aclaraciones.plazo_cambio || "30 dias";

    const reqPayload = {
      formato: formatoComprobante.toLowerCase(),
      tipo: tipo.toLowerCase(),
      emisor: {
        cuit: empresa?.cuit?.toString() || "0",
        razon_social: empresa?.nombre_negocio || "N/A",
        domicilio: empresa?.direccion_negocio || "N/A",
        punto_venta: empresa?.afip_punto_venta_predeterminado || 1,
        condicion_iva: empresa?.afip_condicion_iva || "Responsable Inscripto",
      },
      receptor: {
        nombre_razon_social: tipoClienteSeleccionado.id === "0" ? "Consumidor Final" : clienteSeleccionado?.nombre_razon_social ?? "N/A",
        cuit_o_dni: tipoClienteSeleccionado.id === "0" ? cuitManual || "0" : clienteSeleccionado?.cuit || clienteSeleccionado?.identificacion_fiscal || "0",
        domicilio: "Sin especificar",
        condicion_iva: tipoClienteSeleccionado.id === "0" ? "Consumidor Final" : clienteSeleccionado?.condicion_iva ?? "Consumidor Final"
      },
      transaccion,
      incluir_ticket_cambio: incluirTicketCambio,
      plazo_cambio: plazoCambio
    };

    try {
      const respComp = await fetch("https://sistema-ima.sistemataup.online/api/comprobantes/generar", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(reqPayload)
      });

      if (!respComp.ok) {
        const errorComp = await respComp.json();
        throw new Error(errorComp.detail || "Error desconocido");
      }

      const blob = await respComp.blob();
      const url = URL.createObjectURL(blob);

      // Descarga automática de respaldo
      const link = document.createElement('a');
      link.href = url;
      link.download = `Comprobante_${tipo}_${Date.now()}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Impresión silenciosa con iframe
      const iframe = document.createElement('iframe');
      iframe.style.display = 'none';
      iframe.src = url;
      document.body.appendChild(iframe);

      iframe.onload = () => {
        iframe.contentWindow?.print();
        setTimeout(() => {
          document.body.removeChild(iframe);
          URL.revokeObjectURL(url);
        }, 10000); // Dar tiempo para que se envíe a la cola de impresión
      };

      toast.success("✅ Comprobante enviado a impresión.");
      console.log(`[${new Date().toISOString()}] Impresión enviada correctamente.`);
    } catch (error) {
      console.error("Error al imprimir:", error);
      toast.error("❌ Fallo al intentar generar el comprobante.", {
        action: {
          label: "Reintentar",
          onClick: () => imprimirComprobante(tipo, items, totalFinal, descGeneral, descGeneralPor, obs)
        },
        duration: 8000
      });
    }

  }, [token, empresa, formatoComprobante, tipoClienteSeleccionado, clienteSeleccionado, cuitManual]);

  const procesarVenta = useCallback(async (tipo: string) => {
    // 1. Validaciones
    if (!checkoutVisible) {
      toast.error("Por favor seleccione método de pago primero (Sección Finalizar Compra)");
      setCheckoutVisible(true);
      setTimeout(() => {
        checkoutSectionRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
      return;
    }

    if (productosVendidos.length === 0) {
      toast.error("❌ No hay productos cargados en la venta.");
      return;
    }

    // Validación de método de pago
    if (!usarPagosMultiples) {
      if (!metodoPago) {
        toast.error("❌ Debe seleccionar un método de pago.");
        return;
      }
      if (metodoPago === "efectivo" && montoPagado < totalVentaFinal) {
        toast.error("❌ El monto abonado no puede ser menor al valor final del pedido.");
        return;
      }
    } else {
      // Validación de pagos múltiples
      if (pagosMultiples.length === 0) {
        toast.error("❌ Debe agregar al menos un método de pago.");
        return;
      }

      const sumaPagos = pagosMultiples.reduce((sum, p) => sum + p.monto, 0);

      // Permite un margen de +/- 1 peso por redondeos
      if (Math.abs(sumaPagos - totalVentaFinal) > 1) {
        toast.error(`❌ Diferencia: La suma de pagos ($${sumaPagos.toFixed(2)}) no coincide con el total ($${totalVentaFinal.toFixed(2)}). Diferencia: $${Math.abs(sumaPagos - totalVentaFinal).toFixed(2)}`);
        return;
      }
    }

    if (tipoClienteSeleccionado.id === "1" && !clienteSeleccionado) {
      toast.error("❌ Debe seleccionar un cliente registrado.");
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

    setIsLoading(true);

    // Determinar un tipo_comprobante_solicitado más específico
    let tipoSolicitadoPayload = tipo.toLowerCase();
    if (tipo === "comprobante") {
      tipoSolicitadoPayload = "recibo";
    }
    const cuitReceptor = tipoClienteSeleccionado.id === "0" ? (cuitManual || "0") : (clienteSeleccionado?.cuit || clienteSeleccionado?.identificacion_fiscal || "0");
    if (tipo === "factura") {
      if (cuitReceptor && cuitReceptor.toString().length === 11) {
        tipoSolicitadoPayload = "factura_a";
      } else {
        tipoSolicitadoPayload = "factura_b";
      }
    }

    // --- VALIDACIÓN MEJORADA DE PRODUCTOS EN CARRITO ---
    // Buscar productos no encontrados y dar diagnóstico
    const productosNoEncontrados = productosVendidos.filter((p) => {
      if (p.id) return false;
      const encontrado = productos.find((prod) => prod.nombre === p.tipo);
      return !encontrado;
    });

    if (productosNoEncontrados.length > 0) {
      const nombresNoEncontrados = productosNoEncontrados.map(p => `"${p.tipo}"`).join(", ");
      const sugerencia = productosNoEncontrados.length === 1
        ? `El producto ${nombresNoEncontrados} no está en el catálogo cargado. Intente refrescar el catálogo o verificar el nombre exacto.`
        : `Los productos ${nombresNoEncontrados} no están en el catálogo cargado. Haga clic en 🔄 para refrescar.`;

      toast.error(`❌ ${sugerencia}`);
      setIsLoading(false);
      return;
    }

    // --- VALIDACIÓN ORIGINAL DE IDs ---
    // Calcular el precio de lista total (sin ningún descuento)
    const totalLista = productosVendidos.reduce((acc, p) => {
      return acc + (p.precioBase || 0);
    }, 0);

    // 2. Calcular el total neto (lo que paga el cliente antes de recargos)
    // totalVenta ya incluye descuentos por ítem.
    const totalConDescuento = Math.max(0, totalVenta * (1 - (descuentoSobreTotal || 0) / 100) - (descuentoNominalTotal || 0));

    // 3. El descuento total es la diferencia
    const descuentoTotalCalculado = Math.max(0, totalLista - totalConDescuento);

    const articulosSinId = productosVendidos
      .map((p) => {
        const productoReal = p.id
          ? productos.find((prod) => prod.id === p.id)
          : productos.find((prod) => prod.nombre === p.tipo);
        return {
          nombre: p.tipo,
          id: p.id ?? productoReal?.id,
        };
      })
      .filter((item) => !item.id || Number(item.id) <= 0);

    if (articulosSinId.length > 0) {
      const nombres = articulosSinId.map((item) => item.nombre).join(", ");
      toast.error(`❌ Hay artículos sin ID válido: ${nombres}. Revise el producto seleccionado.`);
      setIsLoading(false);
      return;
    }

    const ventaPayload: any = {
      id_cliente: tipoClienteSeleccionado.id === "0" ? 0 : clienteSeleccionado?.id ?? 0,
      total_venta: totalConDescuento, // Enviamos el total NETO para cálculo correcto de recargos
      descuento_total: descuentoTotalCalculado, // Nuevo campo para historial
      paga_con: montoPagado,
      pago_separado: pagoDividido,
      detalles_pago_separado: detallePagoDividido,
      tipo_comprobante_solicitado: tipoSolicitadoPayload,
      quiere_factura: tipo === "factura",
      articulos_vendidos: productosVendidos.map((p) => {
        const productoReal = p.id
          ? productos.find((prod) => prod.id === p.id)
          : productos.find((prod) => prod.nombre === p.tipo);
        const precioUnitario = productoReal
          ? getPrecioProducto(productoReal)
          : (p.cantidad ? p.precioBase / p.cantidad : 0);
        return {
          id_articulo: p.id ?? productoReal?.id ?? "0",
          nombre: productoReal?.nombre ?? p.tipo,
          cantidad: p.cantidad,
          precio_unitario: precioUnitario,
          subtotal: p.precioTotal,
          tasa_iva: 21.0
        };
      })
    };

    // Agregar información de pago (simple o múltiple)
    if (usarPagosMultiples) {
      ventaPayload.pagos_multiples = pagosMultiples.map((p) => ({
        metodo_pago: p.metodo_pago,
        monto: p.monto,
      }));
    } else {
      ventaPayload.metodo_pago = metodoPago.toUpperCase();
      ventaPayload.paga_con = montoPagado;
    }

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

      // Actualizamos el Store
      await refrescarProductos();

      // Preparar datos para impresión
      const itemsBase = productosVendidos.map((p): ItemComprobante => {
        const productoReal = p.id
          ? productos.find((prod) => prod.id === p.id)
          : productos.find((prod) => prod.nombre === p.tipo);
        const precioUnitario = productoReal
          ? getPrecioProducto(productoReal)
          : (p.cantidad ? p.precioBase / p.cantidad : 0);
        const item: ItemComprobante = {
          descripcion: productoReal?.nombre || p.tipo,
          cantidad: p.cantidad,
          precio_unitario: precioUnitario,
          subtotal: p.precioTotal,
          tasa_iva: 21
        };
        if (tipo !== "factura") {
          item.descuento_especifico = p.descuentoNominal || 0;
          item.descuento_especifico_por = p.porcentajeDescuento || 0;
        }
        return item;
      });

      // Imprimir
      await imprimirComprobante(
        tipo,
        itemsBase,
        totalVentaFinal,
        descuentoNominalTotal || 0,
        descuentoSobreTotal || 0,
        observaciones || ""
      );

      // Reset
      resetFormularioVenta();
      window.scrollTo({ top: 0, behavior: "smooth" });

    } catch (error) {
      console.error("Detalles del error de registro:", error);
      toast.error("❌ Error de red al registrar la venta.");
    } finally {
      setIsLoading(false);
    }
  }, [
    checkoutVisible,
    productosVendidos,
    metodoPago,
    montoPagado,
    totalVentaFinal,
    tipoClienteSeleccionado,
    clienteSeleccionado,
    totalVenta,
    cuitManual,
    pagoDividido,
    detallePagoDividido,
    productos,
    getPrecioProducto,
    empresa,
    token,
    refrescarProductos,
    descuentoNominalTotal,
    descuentoSobreTotal,
    observaciones,
    imprimirComprobante,
    resetFormularioVenta,
    pagosMultiples,
    usarPagosMultiples
  ]);

  const handleF5 = useCallback(() => {
    setTipoFacturacion('recibo');
    procesarVenta('recibo');
  }, [procesarVenta]);

  const handleF6 = useCallback(() => {
    setTipoFacturacion('factura');
    procesarVenta('factura');
  }, [procesarVenta]);

  const handleF8 = useCallback(() => {
    setMetodoPago('efectivo');
    setMontoPagado(totalVentaFinal);
    setInputEfectivo(formatearMoneda(totalVentaFinal.toString()));
    setCheckoutVisible(true);
    setTipoFacturacion('recibo');
    toast.info("✅ Pago EFECTIVO listo - Click en 'Registrar Venta'");
  }, [totalVentaFinal, setMetodoPago, setMontoPagado, formatearMoneda]);

  const handleF9 = useCallback(() => {
    setMetodoPago('transferencia');
    setMontoPagado(totalVentaFinal);
    setCheckoutVisible(true);
    setTipoFacturacion('recibo');
    toast.info("✅ Pago TRANSFERENCIA listo - Click en 'Registrar Venta'");
  }, [totalVentaFinal, setMetodoPago, setMontoPagado]);

  const handleF10 = useCallback(() => {
    setMetodoPago('bancario');
    setMontoPagado(totalVentaFinal);
    setCheckoutVisible(true);
    setTipoFacturacion('recibo');
    toast.info("✅ Pago POS listo - Click en 'Registrar Venta'");
  }, [totalVentaFinal, setMetodoPago, setMontoPagado]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'F5') {
        e.preventDefault();
        handleF5();
      } else if (e.key === 'F6') {
        e.preventDefault();
        handleF6();
      } else if (e.key === 'F8') {
        e.preventDefault();
        handleF8();
      } else if (e.key === 'F9') {
        e.preventDefault();
        handleF9();
      } else if (e.key === 'F10') {
        e.preventDefault();
        handleF10();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handleF5, handleF6, handleF8, handleF9, handleF10]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    procesarVenta(tipoFacturacion);
  }, [procesarVenta, tipoFacturacion]);

  useEffect(() => {
    if (autoSubmitFlag) {
      setAutoSubmitFlag(false);
      setTimeout(() => {
        const e = { preventDefault: () => { } } as unknown as React.FormEvent;
        handleSubmit(e);
      }, 300);
    }
  }, [autoSubmitFlag, handleSubmit]);


  /* Renderizado del Componente */
  return (
    <form onSubmit={handleSubmit} className="flex flex-col w-full lg:w-1/2 rounded-xl bg-white shadow-md">

      {/* Header del Form */}
      <div className="w-full flex flex-row justify-between items-center px-6 py-4 bg-green-700 rounded-t-xl">
        <div className="flex items-center gap-3">
          <h4 className="text-xl font-semibold text-white">Cajero</h4>

          {/* Indicador de Sincronización Automática */}
          <div className="text-xs text-green-100 flex items-center gap-2">
            {isSyncing ? (
              <>
                <span className="inline-block animate-spin h-3 w-3 border-2 border-white border-t-transparent rounded-full"></span>
                <span>Sincronizando...</span>
              </>
            ) : lastSyncTime ? (
              <>
                <span className="text-green-200">✓</span>
                <span>Última sync: {lastSyncTime.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
              </>
            ) : (
              <>
                <span className="text-yellow-200">⏱</span>
                <span>Preparando sincronización...</span>
              </>
            )}
          </div>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-white hover:bg-green-600 hover:text-white"
                  onClick={() => {
                    setBalanzaRetry(p => p + 1);
                    toast.info("Reconectando balanza...");
                  }}
                >
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Reconectar Balanza</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
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

              <div className="flex flex-col gap-4 mt-4 p-4 border rounded-md bg-gray-50">
                <Label className="font-semibold text-green-900">Configuración Adicional de Venta</Label>
                <div className="flex flex-col gap-2">
                  <Label>Observaciones (opcional)</Label>
                  <Textarea
                    placeholder="Notas internas o para el cliente..."
                    value={observaciones}
                    onChange={(e) => setObservaciones(e.target.value)}
                    className="text-black bg-white"
                  />
                </div>
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
            persistirProducto={persistirProducto}
            setPersistirProducto={setPersistirProducto}
            onRefrescarProductos={refrescarProductos}
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
                {!usarPagosMultiples ? (
                  <div className="flex gap-2 w-full md:max-w-1/2">
                    <Select value={metodoPago} onValueChange={setMetodoPago}>
                      <SelectTrigger className="w-full cursor-pointer text-black flex-1">
                        <SelectValue placeholder="Seleccionar método" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="efectivo">Efectivo</SelectItem>
                        <SelectItem value="transferencia">Transferencia</SelectItem>
                        <SelectItem value="bancario">POS</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setUsarPagosMultiples(true)
                        setPagosMultiples([])
                      }}
                      className="border-green-700 text-green-700"
                    >
                      ↓ Múltiples
                    </Button>
                  </div>
                ) : null}
              </div>

              {usarPagosMultiples && (
                <PagoMultiple
                  pagos={pagosMultiples}
                  totalVenta={totalVentaFinal}
                  onPagosChange={setPagosMultiples}
                  onToggleMode={() => {
                    setUsarPagosMultiples(false)
                    setPagosMultiples([])
                  }}
                />
              )}

              {!usarPagosMultiples && metodoPago === 'efectivo' && (
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

            <div className="flex items-center justify-between">
              <Label htmlFor="pagoDividido" className="flex items-center gap-2 text-green-950 text-md font-medium cursor-pointer">
                <Input
                  id="pagoDividido"
                  type="checkbox"
                  checked={pagoDividido}
                  onChange={(e) => {
                    setPagoDividido(e.target.checked)
                    setUsarPagosMultiples(e.target.checked)
                    if (e.target.checked) {
                      setPagosMultiples([])
                    }
                  }}
                  className="h-5 w-5 text-green-700 border-gray-300 rounded focus:ring-green-600 cursor-pointer"
                />
                <span>¿Paga de dos o mas formas?</span>
              </Label>
              {usarPagosMultiples && (
                <span className="text-xs bg-green-300 text-green-900 px-3 py-1 rounded-full font-semibold">
                  🟢 MODO MÚLTIPLE ACTIVO
                </span>
              )}
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

            <Button type="submit" disabled={isLoading} className={`!py-6 bg-green-900 flex items-center justify-center gap-2 ${isLoading ? "cursor-not-allowed opacity-50" : "hover:bg-green-700 cursor-pointer"}`}>
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {isLoading ? "Registrando..." : "Registrar Venta"}
            </Button>
          </div>
        )}
      </div>
    </form>
  )
};

export default FormVentas;
