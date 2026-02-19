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
    const debounceRef = useRef<NodeJS.Timeout | undefined>(undefined)
    const dropdownRef = useRef<HTMLDivElement>(null)

    // Cerrar dropdown al hacer click fuera
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const inputElement = inputRef && 'current' in inputRef ? inputRef.current : null

            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                if (!inputElement || !inputElement.contains(event.target as Node)) {
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

    // Búsqueda simple: solo cuando hay 3+ caracteres
    useEffect(() => {
        const q = (codigo || "").trim().toLowerCase()

        window.clearTimeout(debounceRef.current)

        // Si menos de 3 caracteres, no buscar
        if (q.length < 3) {
            setMatches([])
            setPopoverOpen(false)
            return
        }

        debounceRef.current = setTimeout(async () => {
            setLoading(true)
            try {
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
            } catch (error) {
                console.error("Error buscando productos:", error)
                setMatches([])
            } finally {
                setLoading(false)
            }
        }, 300)

        return () => {
            if (debounceRef.current) clearTimeout(debounceRef.current)
        }
    }, [codigo])

    const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        // ESCAPE: Cerrar el dropdown
        if (e.key === "Escape") {
            e.preventDefault()
            setPopoverOpen(false)
            return
        }

        // ENTER: Solo para código de barras cuando NO hay búsqueda activa
        if (e.key === "Enter" && codigo.length < 3) {
            handleKeyDown(e)
            return
        }
    }

    return (
        <div className="flex flex-col gap-6">
            {/* INPUT DE BÚSQUEDA */}
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
                                onChange={(e) => setCodigoEscaneado(e.target.value)}
                                onKeyDown={onKeyDown}
                                className="border w-full font-semibold"
                                autoFocus
                                placeholder="Escanee o escriba (mín. 3 letras)"
                            />

                            {/* DROPDOWN DE RESULTADOS */}
                            {popoverOpen && (
                                <div
                                    ref={dropdownRef}
                                    className="absolute z-50 w-full mt-1 bg-white border rounded-md shadow-lg max-h-[50vh] overflow-auto"
                                >
                                    <Command shouldFilter={false}>
                                        {loading ? (
                                            <div className="py-4 text-center text-gray-500">🔍 Buscando...</div>
                                        ) : matches.length === 0 ? (
                                            <CommandEmpty>
                                                <div className="py-4 text-center text-red-500">❌ No encontrado</div>
                                            </CommandEmpty>
                                        ) : (
                                            <CommandGroup>
                                                {matches.map((prod) => (
                                                    <CommandItem
                                                        key={prod.id}
                                                        value={prod.nombre}
                                                        onMouseDown={(e) => e.preventDefault()}
                                                        onClick={() => {
                                                            setProductoSeleccionado(prod)
                                                            setCodigoEscaneado(prod.nombre)
                                                            setPopoverOpen(false)
                                                            // Restaurar foco al input
                                                            if (inputRef && 'current' in inputRef && inputRef.current) {
                                                                inputRef.current.focus()
                                                            }
                                                        }}
                                                        className="cursor-pointer transition-colors hover:bg-green-100"
                                                    >
                                                        <div className="flex items-center justify-between w-full">
                                                            <span className="truncate font-medium">{prod.nombre}</span>
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
                                        )}
                                    </Command>
                                </div>
                            )}
                        </div>

                        {/* BOTONES */}
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
