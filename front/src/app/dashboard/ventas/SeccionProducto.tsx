"use client"

import { LegacyRef, useEffect, useRef, useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandItem, CommandInput } from "@/components/ui/command"
import { ChevronsUpDown, ChevronsDown, RefreshCw, Lock } from "lucide-react"
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
  const debounceRef = useRef<number | undefined>(undefined)

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
      setPopoverOpen(mapped.length > 0)
      setLoading(false)
    }, 250)

    return () => window.clearTimeout(debounceRef.current)
  }, [codigo, setPopoverOpen])

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && matches.length > 0) {
      e.preventDefault()
      setProductoSeleccionado(matches[0])
      setCodigoEscaneado(matches[0].nombre)
      setPopoverOpen(false)
      return
    }
    if (e.key === "ArrowDown") {
      e.preventDefault()
      const all = productos.slice(0, 200)
      setMatches(all)
      setPopoverOpen(true)
      return
    }
    handleKeyDown(e)
  }

  return (
    // Usamos un div contenedor con flex-col y gap para espaciar las secciones internas
    <div className="flex flex-col gap-6">

      {/* --- ÚNICO INPUT: CÓDIGO / TEXTO DEL SCANNER --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-center">
        <Label htmlFor="codigo-barras" className="text-lg font-semibold text-green-900 md:text-right">
          Escáner / Código
        </Label>
        <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
          <div className="md:col-span-2 flex gap-2">
            <PopoverTrigger asChild>
              <Input
                id="codigo-barras"
                ref={inputRef}
                type="text"
                value={codigo}
                onChange={(e) => setCodigoEscaneado(e.target.value)}
                onKeyDown={onKeyDown}
                onFocus={() => setPopoverOpen(false)}
                className="border w-full"
                autoFocus
                placeholder="Escanee o escriba nombre y presione Enter"
              />
            </PopoverTrigger>
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
          <PopoverContent className="p-0 w-[min(520px,85vw)] max-h-[50vh] overflow-auto" align="start">
            <Command>
              {productoSeleccionado && (
                <div className="px-3 py-2 text-sm flex items-center justify-between border-b">
                  <span className="truncate">{productoSeleccionado.nombre}</span>
                  <span className="text-muted-foreground">${productoSeleccionado.precio_venta.toFixed(2)}</span>
                </div>
              )}
              <CommandInput
                value={codigo}
                onValueChange={(v) => setCodigoEscaneado(v)}
                placeholder="Buscar producto..."
              />
              <CommandEmpty>{loading ? "Buscando..." : "No hay resultados"}</CommandEmpty>
              <CommandGroup heading="Productos">
                {matches.map((prod) => (
                  <CommandItem
                    key={prod.id}
                    value={prod.nombre}
                    onSelect={() => {
                      setProductoSeleccionado(prod)
                      setCodigoEscaneado(prod.nombre)
                      setPopoverOpen(false)
                    }}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="truncate">{prod.nombre}</span>
                      <span className="text-muted-foreground flex items-center gap-1">
                        <ChevronsUpDown className="h-4 w-4" />
                        ${prod.precio_venta.toFixed(2)}
                      </span>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            </Command>
          </PopoverContent>
        </Popover>
      </div>
    </div>
  );
}
