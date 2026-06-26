"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LegacyRef } from "react"

// Definimos las props que el componente necesita
interface SeccionCantidadProps {
  cantidadInputRef: LegacyRef<HTMLInputElement>;
  modoVenta: 'unidad' | 'granel' | 'precio_manual';

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
  cantidadUnidad, setCantidadUnidad, stockActual: _stockActual,
  unidadDeVenta, inputCantidadGranel, handleCantidadGranelChange,
  inputPrecioGranel, handlePrecioGranelChange
}: SeccionCantidadProps) {
  // Sin tope por stock: se permite vender aunque no haya existencias.
  const limiteStock = undefined;

  // --- VISTA PARA MODO 'PRECIO MANUAL' (Panadería, Golosinas, etc.) ---
  if (modoVenta === 'precio_manual') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-center">
        <Label className="text-xl font-semibold text-green-900 md:text-right">
          Precio de venta
        </Label>
        <div className="md:col-span-2">
          <Input
            id="precio-manual"
            ref={cantidadInputRef}
            type="number"
            min={0.01}
            step="0.01"
            placeholder="Ingrese el importe"
            value={inputPrecioGranel}
            onChange={handlePrecioGranelChange}
            className="w-full text-black text-lg"
          />
        </div>
      </div>
    );
  }

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
            max={limiteStock}
            value={cantidadUnidad === 0 ? "" : cantidadUnidad}
            onChange={(e) => {
              const input = e.target.value;
              if (input === "") { setCantidadUnidad(0); return; }
              const parsed = parseInt(input, 10);
              if (isNaN(parsed)) return;
              const siguiente = limiteStock ? Math.min(parsed, limiteStock) : parsed;
              setCantidadUnidad(siguiente);
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