"use client"

import { LegacyRef, useEffect, useRef, useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Command, CommandEmpty, CommandGroup, CommandItem } from "@/components/ui/command"
import { ChevronsDown, RefreshCw, Lock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api-client"

// Tipos
type Producto = {
  id: string;
  nombre: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
  unidad_venta: string;
};
type MinimalArticulo = {
  id: number;
  descripcion: string;
  precio_venta: number;
  venta_negocio?: number;
  stock_actual?: number;
  unidad_venta?: string;
}

// Props que el componente recibe del orquestador (FormVentas)
interface SeccionProductoProps {
  inputRef: LegacyRef<HTMLInputElement>;
  codigo: string;
  setCodigoEscaneado: (codigo: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  productos: Producto[];
  productoSeleccionado: Producto | null;
  setProductoSeleccionado: (producto: Producto | null) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  tipoClienteSeleccionadoId: string;

  popoverOpen: boolean;
  setPopoverOpen: (open: boolean) => void;
  productoEscaneado: Producto | null;
  cantidadEscaneada: number;
  setCantidadEscaneada: (cantidad: number) => void;
  handleAgregarDesdePopover: () => void;

  persistirProducto: boolean;
  setPersistirProducto: (v: boolean) => void;

  onRefrescarProductos: () => void;
}

export function SeccionProducto(props: SeccionProductoProps) {
  const {
    inputRef,
    codigo,
    setCodigoEscaneado,
    handleKeyDown,
    productos,
    productoSeleccionado,
    setProductoSeleccionado,
    popoverOpen,
    setPopoverOpen,
    persistirProducto,
    setPersistirProducto,
    onRefrescarProductos,
  } = props

  const [matches, setMatches] = useState<Producto[]>([])
  const [loading, setLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false) // Detectar si el usuario está escribiendo manualmente
  const [justSelected, setJustSelected] = useState(false) // Flag para evitar reabrir dropdown después de selección
  const debounceRef = useRef<number | undefined>(undefined)
  const typingTimeoutRef = useRef<number | undefined>(undefined)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Cerrar dropdown al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        const inputElement = inputRef && 'current' in inputRef ? inputRef.current : null
        if (inputElement && !inputElement.contains(event.target as Node)) {
          setPopoverOpen(false)
        }
      }
    }

    if (popoverOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [popoverOpen, inputRef, setPopoverOpen])

  useEffect(() => {
    const q = (codigo || "").trim().toLowerCase()

    // Detectar escritura manual (más de 2 caracteres o cambios frecuentes)
    if (q.length > 0) {
      setIsTyping(true)
      window.clearTimeout(typingTimeoutRef.current)
      typingTimeoutRef.current = window.setTimeout(() => {
        setIsTyping(false)
      }, 1500) // Se considera "escribiendo" por 1.5 segundos después del último cambio
    }

    window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(async () => {
      if (!q) {
        setMatches([])
        setPopoverOpen(false)
        setJustSelected(false) // Resetear flag cuando se borra el input
        return
      }

      setLoading(true)
      const resp = await api.articulos.buscar(q, 20)
      const data = (resp.success ? (resp.data as MinimalArticulo[]) : []) || []
      const mapped: Producto[] = data.map((a) => ({
        id: String(a.id),
        nombre: a.descripcion,
        precio_venta: a.precio_venta,
        venta_negocio: a.venta_negocio ?? a.precio_venta,
        stock_actual: a.stock_actual ?? 0,
        unidad_venta: a.unidad_venta ?? "unidad",
      }))
      setMatches(mapped)

      // Solo abrir automáticamente si NO se acaba de seleccionar un producto
      // Y solo si el usuario NO está escribiendo activamente
      if (!justSelected && !isTyping && mapped.length > 0) {
        setPopoverOpen(true)
      }

      setLoading(false)
    }, 500)

    return () => {
      window.clearTimeout(debounceRef.current)
      window.clearTimeout(typingTimeoutRef.current)
    }
  }, [codigo, setPopoverOpen, justSelected])

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // ESCAPE: Cerrar el popover
    if (e.key === "Escape") {
      e.preventDefault()
      setPopoverOpen(false)
      setIsTyping(false)
      return
    }

    // ARROW DOWN: Mostrar productos manualmente (resetea flag de selección)
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setJustSelected(false) // Permitir reabrir manualmente
      if (!codigo.trim()) {
        // Sin texto, mostrar todos
        const all = productos.slice(0, 200)
        setMatches(all)
      }
      // Si ya hay matches, simplemente abrir (o dejar abierto)
      setPopoverOpen(true)
      return
    }

    // ENTER: Solo para código de barras cuando NO está escribiendo
    if (e.key === "Enter" && !isTyping && codigo.trim()) {
      handleKeyDown(e)
      return
    }
  }

  return (
    // Usamos un div contenedor con flex-col y gap para espaciar las secciones internas
    <div className="flex flex-col gap-6">

      {/* --- ÚNICO INPUT: CÓDIGO / TEXTO DEL SCANNER --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-center">
        <Label htmlFor="codigo-barras" className="text-lg font-semibold text-green-900 md:text-right">
          Escáner / Código
        </Label>
        <div className="md:col-span-2">
          <div className="flex gap-2">
            <div className="relative w-full">
              <Input
                id="codigo-barras"
                ref={inputRef}
                type="text"
                value={codigo}
                onChange={(e) => {
                  const newValue = e.target.value
                  setCodigoEscaneado(newValue)
                  setIsTyping(true)

                  // Si el usuario modifica manualmente el texto, resetear flag de selección
                  if (productoSeleccionado && newValue !== productoSeleccionado.nombre) {
                    setJustSelected(false)
                  }
                }}
                onKeyDown={onKeyDown}
                onFocus={() => {
                  // Cuando el input recibe foco, si hay texto, mostrar resultados
                  if (codigo.trim() && matches.length > 0 && !justSelected) {
                    setPopoverOpen(true)
                  }
                }}
                className="border w-full font-semibold"
                autoFocus
                placeholder="Escanee código o escriba el nombre del producto"
              />
              {popoverOpen && (
                <div
                  ref={dropdownRef}
                  className="absolute z-50 w-full mt-1 bg-white border rounded-md shadow-lg max-h-[50vh] overflow-auto"
                >
                  <Command shouldFilter={false}>
                    {productoSeleccionado && (
                      <div className="px-3 py-2 text-sm flex items-center justify-between border-b bg-green-50">
                        <span className="truncate font-semibold text-green-900">
                          ✅ {productoSeleccionado.nombre} 
                          {productoSeleccionado.id ? ` (ID: ${productoSeleccionado.id})` : ' ⚠️ SIN ID'}
                        </span>
                        <span className="text-green-700 font-bold">${productoSeleccionado.precio_venta.toFixed(2)}</span>
                      </div>
                    )}
                    <CommandEmpty>
                      <div className="py-4 text-center">
                        {loading ? (
                          <span className="text-gray-500">🔍 Buscando...</span>
                        ) : codigo ? (
                          <span className="text-red-500">❌ No encontramos "{codigo}"</span>
                        ) : (
                          <span className="text-gray-400">Escribe arriba para buscar</span>
                        )}
                      </div>
                    </CommandEmpty>
                    <CommandGroup heading="Productos">
                      {matches.map((prod, index) => (
                        <CommandItem
                          key={prod.id}
                          value={prod.nombre}
                          onSelect={() => {
                            setProductoSeleccionado(prod)
                            setCodigoEscaneado(prod.nombre)
                            setIsTyping(false)
                            setJustSelected(true) // Marcar que se acaba de seleccionar
                            setPopoverOpen(false)
                          }}
                          onMouseDown={(e) => {
                            // Prevenir que el click quite el foco del input
                            e.preventDefault()
                          }}
                          onClick={() => {
                            setProductoSeleccionado(prod)
                            setCodigoEscaneado(prod.nombre)
                            setIsTyping(false)
                            setJustSelected(true) // Marcar que se acaba de seleccionar
                            setPopoverOpen(false)
                            // Restaurar foco al input después de seleccionar
                            setTimeout(() => {
                              if (inputRef && 'current' in inputRef && inputRef.current) {
                                inputRef.current.focus()
                              }
                            }, 50)
                          }}
                          className="cursor-pointer transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
                        >
                          <div className="flex items-center justify-between w-full">
                            <div className="flex items-center gap-2 flex-1">
                              <span className="truncate font-medium">{prod.nombre}</span>
                              <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded flex-shrink-0">
                                ID: {prod.id}
                              </span>
                            </div>
                            <span className="text-muted-foreground flex items-center gap-2 ml-2 flex-shrink-0">
                              <span className="text-xs">${prod.precio_venta.toFixed(2)}</span>
                              {prod.stock_actual > 0 && (
                                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                                  Stock: {prod.stock_actual}
                                </span>
                              )}
                            </span>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </Command>
                </div>
              )}
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setLoading(true)
                api.articulos.buscar("", 200).then((resp) => {
                  const data = (resp.success ? (resp.data as MinimalArticulo[]) : []) || []
                  const mapped: Producto[] = data.map((a) => ({
                    id: String(a.id),
                    nombre: a.descripcion,
                    precio_venta: a.precio_venta,
                    venta_negocio: a.venta_negocio ?? a.precio_venta,
                    stock_actual: a.stock_actual ?? 0,
                    unidad_venta: a.unidad_venta ?? "unidad",
                  }))
                  setMatches(mapped)
                  setPopoverOpen(true)
                }).finally(() => setLoading(false))
              }}
              aria-label="Ver todos"
            >
              <ChevronsDown className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                onRefrescarProductos()
                setLoading(true)
                api.articulos.buscar("", 100).then((resp) => {
                  const data = (resp.success ? (resp.data as MinimalArticulo[]) : []) || []
                  const mapped: Producto[] = data.map((a) => ({
                    id: String(a.id),
                    nombre: a.descripcion,
                    precio_venta: a.precio_venta,
                    venta_negocio: a.venta_negocio ?? a.precio_venta,
                    stock_actual: a.stock_actual ?? 0,
                    unidad_venta: a.unidad_venta ?? "unidad",
                  }))
                  setMatches(mapped)
                  setPopoverOpen(true)
                }).finally(() => setLoading(false))
              }}
              aria-label="Sincronizar productos"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant={persistirProducto ? "default" : "outline"}
              onClick={() => setPersistirProducto(!persistirProducto)}
              aria-label="Bloquear producto seleccionado"
            >
              <Lock className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
