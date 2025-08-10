// src/app/dashboard)/ventas/SeccionCliente.tsx
"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ChevronsUpDown } from "lucide-react"

// Definimos los tipos que el componente espera recibir
type Cliente = {
  id: number;
  nombre_razon_social: string;
  condicion_iva: string;
  identificacion_fiscal: string | null;
  cuit: string | null;
  telefono: string;
  activo: boolean;
};

type TipoCliente = {
  id: string;
  nombre: string;
};

// Definimos las props del componente
interface SeccionClienteProps {
  tipoClienteSeleccionado: TipoCliente;
  setTipoClienteSeleccionado: (tipo: TipoCliente) => void;
  tiposDeCliente: TipoCliente[];
  cuitManual: string;
  setCuitManual: (cuit: string) => void;
  totalVenta: number;
  clientes: Cliente[];
  clienteSeleccionado: Cliente | null;
  setClienteSeleccionado: (cliente: Cliente | null) => void;
  openCliente: boolean;
  setOpenCliente: (open: boolean) => void;
  busquedaCliente: string;
  setBusquedaCliente: (busqueda: string) => void;
}

export function SeccionCliente({
  tipoClienteSeleccionado, setTipoClienteSeleccionado, tiposDeCliente,
  cuitManual, setCuitManual, totalVenta,
  clientes, clienteSeleccionado, setClienteSeleccionado,
  openCliente, setOpenCliente, busquedaCliente, setBusquedaCliente
}: SeccionClienteProps) {
  return (
    <div className="flex flex-col md:flex-row w-full gap-4 justify-between items-center">
      <Label className="text-2xl font-semibold text-green-900 w-full md:max-w-1/4">Tipo de Cliente</Label>
      <div className="flex flex-col gap-2 w-full md:w-2/3">
        <Select
          defaultValue={tipoClienteSeleccionado.id}
          onValueChange={(value) => {
            const cliente = tiposDeCliente.find(p => p.id === value);
            if (cliente) setTipoClienteSeleccionado(cliente);
          }}
        >
          <SelectTrigger className="w-full cursor-pointer text-black">
            <SelectValue placeholder="Seleccionar cliente" />
          </SelectTrigger>
          <SelectContent>
            {tiposDeCliente.map((p) => (
              <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {tipoClienteSeleccionado.id === "0" && (
          <>
            <Input
              type="text"
              placeholder="Ingresar CUIT del cliente - sin espacios ni puntos"
              value={cuitManual}
              onChange={(e) => setCuitManual(e.target.value)}
              className="mt-1 text-black w-full"
            />
            {totalVenta > 200000 && (
              <p className="text-sm text-red-600 font-semibold mt-1">
                ⚠️ Para ventas mayores a $200.000 el CUIT es obligatorio.
              </p>
            )}
          </>
        )}

        {tipoClienteSeleccionado.id === "1" && (
          <div className="w-full flex flex-col gap-2">
            {!clientes.length ? (
              <p className="text-green-900 font-semibold">Cargando clientes...</p>
            ) : (
              <Popover open={openCliente} onOpenChange={setOpenCliente}>
                <PopoverTrigger asChild>
                  <button 
                    role="combobox" 
                    aria-expanded={openCliente} 
                    aria-controls="clientes-lista" // Este apunta al ID de abajo
                    className="w-full justify-between text-left cursor-pointer border px-3 py-2 rounded-md shadow-sm bg-white text-black flex items-center"
                  >
                    {clienteSeleccionado ? `${clienteSeleccionado.nombre_razon_social} (${clienteSeleccionado.cuit || "Sin CUIT"})` : "Seleccionar cliente"}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </button>
                </PopoverTrigger>
                <PopoverContent side="bottom" align="start" className="w-full md:max-w-[98%] p-0 max-h-64 overflow-y-auto z-50" sideOffset={8}>
                  {/* === MODIFICACIÓN CLAVE AQUÍ === */}
                  <Command id="clientes-lista"> 
                  {/* === FIN DE LA MODIFICACIÓN === */}
                    <CommandInput placeholder="Buscar cliente por nombre o CUIT..." value={busquedaCliente} onValueChange={setBusquedaCliente} />
                    <CommandEmpty>No se encontró ningún cliente.</CommandEmpty>
                    <CommandGroup>
                      {clientes.filter(cliente => cliente.nombre_razon_social.toLowerCase().includes(busquedaCliente.toLowerCase()) || cliente.cuit?.toString().includes(busquedaCliente)).map((cliente) => (
                        <CommandItem key={cliente.id} value={`${cliente.nombre_razon_social} ${cliente.cuit || ""}`} className="pl-2 pr-4 py-2 text-sm text-black cursor-pointer" onSelect={() => { setClienteSeleccionado(cliente); setOpenCliente(false); }}>
                          <span className="truncate">{cliente.nombre_razon_social} ({cliente.cuit || "Sin CUIT"})</span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </Command>
                </PopoverContent>
              </Popover>
            )}
          </div>
        )}
      </div>
    </div>
  );
}