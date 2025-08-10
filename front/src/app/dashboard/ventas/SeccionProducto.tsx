// src/app/dashboard)/ventas/SeccionProductos.tsx

"use client"

import { LegacyRef } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command"
import { ChevronsUpDown } from "lucide-react"

// Tipos
type Producto = {
  id: string;
  nombre: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
  unidad_venta: string;
};

// Props
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
}

export function SeccionProducto({
  inputRef, codigo, setCodigoEscaneado, handleKeyDown,
  productos, productoSeleccionado, setProductoSeleccionado,
  open, setOpen, tipoClienteSeleccionadoId
}: SeccionProductoProps) {
  return (
    <>
      {/* Código de Barras */}
      <div className="w-full flex flex-col md:flex-row gap-4 items-start md:items-center">
        <Label className="text-2xl font-semibold text-green-900 text-left">Código de Barras</Label>
        <Input ref={inputRef} type="text" value={codigo} onChange={(e) => setCodigoEscaneado(e.target.value)} onKeyDown={handleKeyDown} className="border w-full md:max-w-2/3" autoFocus />
      </div>

      {/* Dropdown de Productos */}
      <div className="flex flex-col gap-4 items-start justify-between md:flex-row md:items-center">
        <Label className="text-2xl font-semibold text-green-900">Producto</Label>
        {productos.length === 0 ? (
          <p className="text-green-900 font-semibold">Cargando productos...</p>
        ) : (
          <div className="w-full md:max-w-2/3 flex flex-col gap-2">
            <Popover open={open} onOpenChange={setOpen}>
              <PopoverTrigger asChild>
                <button
                  role="combobox"
                  aria-expanded={open}
                  aria-controls="productos-lista" // Este apunta al ID de abajo
                  className="w-full justify-between text-left cursor-pointer border px-3 py-2 rounded-md shadow-sm bg-white text-black flex items-center"
                  onClick={() => setOpen(!open)}
                >
                  {productoSeleccionado ? `${productoSeleccionado.nombre} - $${tipoClienteSeleccionadoId === "1" ? productoSeleccionado.venta_negocio : productoSeleccionado.precio_venta}` : "Seleccionar producto"}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </button>
              </PopoverTrigger>
              <PopoverContent side="bottom" align="start" className="w-full md:max-w-[98%] p-0 max-h-64 overflow-y-auto z-50" sideOffset={8}>
                {/* === MODIFICACIÓN CLAVE AQUÍ === */}
                <Command id="productos-lista">
                {/* === FIN DE LA MODIFICACIÓN === */}
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
          </div>
        )}
      </div>
    </>
  );
}