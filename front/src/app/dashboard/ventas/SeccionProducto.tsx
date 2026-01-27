"use client"

import { LegacyRef } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command"
import { ChevronsUpDown, Lock, LockOpen, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"

// Tipos
type Producto = {
  id: string;
  nombre: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
  unidad_venta: string;
};

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

  // Nuevas props para el Popover de cantidad
  popoverOpen: boolean;
  setPopoverOpen: (open: boolean) => void;
  productoEscaneado: Producto | null;
  cantidadEscaneada: number;
  setCantidadEscaneada: (cantidad: number) => void;
  handleAgregarDesdePopover: () => void;

  // Persistencia de producto
  persistirProducto: boolean;
  setPersistirProducto: (v: boolean) => void;

  // Sincronización manual
  onRefrescarProductos: () => void;
}

export function SeccionProducto({
  inputRef, codigo, setCodigoEscaneado, handleKeyDown,
  productos, productoSeleccionado, setProductoSeleccionado,
  open, setOpen, tipoClienteSeleccionadoId,
  popoverOpen, setPopoverOpen, productoEscaneado,
  cantidadEscaneada, setCantidadEscaneada, handleAgregarDesdePopover,
  persistirProducto, setPersistirProducto,
  onRefrescarProductos
}: SeccionProductoProps) {
  return (
    // Usamos un div contenedor con flex-col y gap para espaciar las secciones internas
    <div className="flex flex-col gap-6">

      {/* --- CÓDIGO DE BARRAS ALINEADO --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-center">
        <Label htmlFor="codigo-barras" className="text-lg font-semibold text-green-900 md:text-right">
          Código de Barras
        </Label>
        <div className="md:col-span-2">
          <Popover open={popoverOpen} onOpenChange={setPopoverOpen}>
            <PopoverTrigger asChild>
              <Input
                id="codigo-barras"
                ref={inputRef}
                type="text"
                value={codigo}
                onChange={(e) => setCodigoEscaneado(e.target.value)}
                onKeyDown={handleKeyDown}
                className="border w-full"
                autoFocus
              />
            </PopoverTrigger>
            <PopoverContent className="w-80">
              {productoEscaneado && (
                <div className="grid gap-4">
                  <div className="space-y-2">
                    <h4 className="font-medium leading-none">Agregar Producto</h4>
                    <p className="text-sm text-muted-foreground">{productoEscaneado.nombre}</p>
                  </div>
                  <div className="grid gap-2">
                    <div className="grid grid-cols-3 items-center gap-4">
                      <Label htmlFor="cantidad-popover">Cantidad</Label>
                      <Input
                        id="cantidad-popover"
                        type="number"
                        min={1}
                        value={cantidadEscaneada}
                        onChange={(e) => setCantidadEscaneada(Number(e.target.value))}
                        className="col-span-2 h-8"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleAgregarDesdePopover();
                          }
                        }}
                      />
                    </div>
                  </div>
                  <Button onClick={handleAgregarDesdePopover}>Agregar</Button>
                </div>
              )}
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* --- PRODUCTO ALINEADO --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-center">
        <Label className="text-xl font-semibold text-green-900 md:text-right">
          Producto
        </Label>
        <div className="md:col-span-2 flex gap-2">
          <div className="flex-1">
            {productos.length === 0 ? (
              <div className="flex items-center text-green-900 font-semibold">
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Cargando...
              </div>
            ) : (
              <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                  <button
                    aria-label="Seleccionar un producto"
                    role="combobox"
                    aria-expanded={open}
                    aria-controls="productos-lista"
                    className="w-full justify-between text-left cursor-pointer border px-3 py-2 rounded-md shadow-sm bg-white text-black flex items-center"
                    onClick={() => setOpen(!open)}
                  >
                    {productoSeleccionado ? `${productoSeleccionado.nombre} - $${tipoClienteSeleccionadoId === "1" ? productoSeleccionado.venta_negocio : productoSeleccionado.precio_venta}` : "Seleccionar producto"}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </button>
                </PopoverTrigger>
                <PopoverContent side="bottom" align="start" className="w-full p-0 max-h-64 overflow-y-auto z-50" sideOffset={8}>
                  <Command id="productos-lista">
                    <CommandInput placeholder="Buscar producto..." />
                    <CommandEmpty>No se encontró ningún producto.</CommandEmpty>
                    <CommandGroup>
                      {productos.map((p) => (
                        <CommandItem key={p.id} value={p.nombre} className="pl-2 pr-4 py-2 text-sm text-black cursor-pointer" onSelect={() => { setProductoSeleccionado(p); setOpen(false); }}>
                          <span className="truncate">{p.nombre} | ${tipoClienteSeleccionadoId === "1" ? p.venta_negocio : p.precio_venta} | Stock: {p.stock_actual}</span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </Command>
                </PopoverContent>
              </Popover>
            )}
          </div>
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={onRefrescarProductos}
            title="Sincronizar productos"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            variant={persistirProducto ? "default" : "outline"}
            size="icon"
            onClick={() => setPersistirProducto(!persistirProducto)}
            title={persistirProducto ? "Producto persistente (No se borrará al agregar)" : "Producto se limpiará al agregar"}
          >
            {persistirProducto ? <Lock className="h-4 w-4" /> : <LockOpen className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}