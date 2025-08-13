"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LegacyRef } from "react"

// Definimos las props que el componente necesita
interface SeccionCantidadProps {
  cantidadInputRef: LegacyRef<HTMLInputElement>;
  modoVenta: 'unidad' | 'granel';
  
  // Props para modo 'unidad'
  cantidadUnidad: number;
  setCantidadUnidad: (value: number) => void;
  stockActual: number;

  // Props para modo 'granel'
  unidadDeVenta: string;
  inputCantidadGranel: string;
  handleCantidadGranelChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  inputPrecioGranel: string;
  handlePrecioGranelChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function SeccionCantidad({
  cantidadInputRef,
  modoVenta,
  cantidadUnidad, setCantidadUnidad, stockActual,
  unidadDeVenta, inputCantidadGranel, handleCantidadGranelChange,
  inputPrecioGranel, handlePrecioGranelChange
}: SeccionCantidadProps) {

  // --- VISTA PARA MODO 'UNIDAD' ---
  if (modoVenta === 'unidad') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-center">
        <Label htmlFor="cantidad-unidad" className="text-xl font-semibold text-green-900 md:text-right">
          Cantidad
        </Label>
        <div className="md:col-span-2">
          <Input
            id="cantidad-unidad"
            ref={cantidadInputRef}
            type="number"
            onWheel={(e) => (e.target as HTMLInputElement).blur()}
            min={1}
            max={stockActual || 9999}
            value={cantidadUnidad === 0 ? "" : cantidadUnidad}
            onChange={(e) => {
              const input = e.target.value;
              if (input === "") { setCantidadUnidad(0); return; }
              const parsed = parseInt(input, 10);
              if (isNaN(parsed)) return;
              const max = stockActual ?? Infinity;
              setCantidadUnidad(Math.min(parsed, max));
            }}
            className="w-full text-black"
          />
        </div>
      </div>
    );
  }

  // --- VISTA PARA MODO 'GRANEL' ---
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-center">
        <Label className="text-xl font-semibold text-green-900 md:text-right">
          Cantidad / Precio
        </Label>
        <div className="md:col-span-2 grid grid-cols-2 gap-x-4">
            {/* Input de Cantidad (Kg, Lt, etc.) */}
            <div className="flex flex-col gap-2">
                <Label htmlFor="cantidad-granel" className="text-sm text-muted-foreground">
                    ({unidadDeVenta})
                </Label>
                <Input
                  id="cantidad-granel"
                  ref={cantidadInputRef}
                  type="number"
                  value={inputCantidadGranel}
                  onChange={handleCantidadGranelChange}
                  step="0.01"
                  className="w-full text-black"
                />
            </div>
            
            {/* Input de Precio ($) */}
            <div className="flex flex-col gap-2">
                <Label htmlFor="precio-granel" className="text-sm text-muted-foreground">
                    ($)
                </Label>
                <Input
                  id="precio-granel"
                  type="number"
                  value={inputPrecioGranel}
                  onChange={handlePrecioGranelChange}
                  step="0.01"
                  className="w-full text-black"
                />
            </div>
        </div>
    </div>
  );
}