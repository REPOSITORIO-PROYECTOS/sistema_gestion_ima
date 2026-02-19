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

    window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(async () => {
      if (!q) {
        setMatches([])
        setPopoverOpen(false)
        return
      }

      setLoading(true)
      // ✅ Buscar solo 4 coincidencias máximo
      const resp = await api.articulos.buscar(q, 4)
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

      // ✅ Abrir el dropdown si hay coincidencias (simple y directo)
      if (mapped.length > 0) {
        setPopoverOpen(true)
        setJustSelected(false) // Resetear flag para permitir más búsquedas
      }

      setLoading(false)
    }, 300) // ✅ Debounce rápido para respuesta inmediata

    return () => {
      window.clearTimeout(debounceRef.current)
    }
  }, [codigo, setPopoverOpen])

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

                  // Si el usuario modifica el texto después de seleccionar, resetear para nueva búsqueda
                  if (productoSeleccionado && newValue !== productoSeleccionado.nombre) {
                    setJustSelected(false) // ✅ Permite que se reabre la búsqueda si escribe diferente
                    setProductoSeleccionado(null) // Limpiar selección anterior
                  }
                }}
                onKeyDown={onKeyDown}
                onFocus={() => {
                  // Al recibir foco: si hay texto y está escribiendo (no acaba de seleccionar), abrir dropdown
                  if (codigo.trim() && matches.length > 0 && !justSelected) {
                    setPopoverOpen(true)
                  }
                }}
                className="border w-full font-semibold"
                autoFocus
                placeholder="Escribe código o nombre (máximo 3-4 coincidencias)"
              />
              {popoverOpen && (
                <div
                  ref={dropdownRef}
                  className="absolute z-50 w-full mt-1 bg-white border border-green-300 rounded-md shadow-lg max-h-80 overflow-y-auto"
                >
                  <Command shouldFilter={false}>
                    {productoSeleccionado && (
                      <div className="px-3 py-2 text-sm flex items-center justify-between border-b bg-green-50">
                        <span className="font-semibold text-green-900 text-xs">
                          ✅ Seleccionado: {productoSeleccionado.nombre} (ID: {productoSeleccionado.id})
                        </span>
                        <span className="text-green-700 font-bold text-xs">${productoSeleccionado.precio_venta.toFixed(2)}</span>
                      </div>
                    )}
                    <CommandEmpty>
                      <div className="py-3 text-center text-sm">
                        {loading ? (
                          <span className="text-gray-500">🔍 Buscando...</span>
                        ) : codigo ? (
                          <span className="text-red-500">❌ No encontrado: "{codigo}"</span>
                        ) : (
                          <span className="text-gray-400">Escribe para buscar...</span>
                        )}
                      </div>
                    </CommandEmpty>
                    <CommandGroup heading="Coincidencias" className="text-xs">
                      {matches.map((prod) => (
                        <CommandItem
                          key={prod.id}
                          value={prod.nombre}
                          onSelect={() => {
                            setProductoSeleccionado(prod)
                            setCodigoEscaneado(prod.nombre) // ✅ Mostrar nombre del producto seleccionado
                            setIsTyping(false)
                            setJustSelected(true)
                            setPopoverOpen(false)
                          }}
                          onMouseDown={(e) => {
                            e.preventDefault()
                          }}
                          onClick={() => {
                            setProductoSeleccionado(prod)
                            setCodigoEscaneado(prod.nombre)
                            setIsTyping(false)
                            setJustSelected(true)
                            setPopoverOpen(false)
                            setTimeout(() => {
                              if (inputRef && 'current' in inputRef && inputRef.current) {
                                inputRef.current.focus()
                              }
                            }, 50)
                          }}
                          className="cursor-pointer text-xs py-1.5 hover:bg-green-50"
                        >
                          <div className="flex items-center justify-between w-full gap-2">
                            <span className="font-medium flex-1">{prod.nombre}</span>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <span className="text-xs text-gray-600">${prod.precio_venta.toFixed(0)}</span>
                              {prod.stock_actual > 0 && (
                                <span className="text-xs bg-blue-100 text-blue-700 px-1 py-0.5 rounded">
                                  {prod.stock_actual}
                                </span>
                              )}
                            </div>
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
