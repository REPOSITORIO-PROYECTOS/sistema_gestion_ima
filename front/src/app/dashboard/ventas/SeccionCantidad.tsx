// src/app/dashboard/ventas/SeccionCantidad.tsx
"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

// Definimos las props que el componente necesita
interface SeccionCantidadProps {
  modoVenta: 'unidad' | 'granel';
  
  // Props para modo 'unidad'
  cantidadUnidad: number;
  setCantidadUnidad: (value: number) => void;
  stockActual: number;

  // Props para modo 'granel'
  unidadDeVenta: string; // Ej: "Kg", "Lt"
  inputCantidadGranel: string;
  handleCantidadGranelChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  inputPrecioGranel: string;
  handlePrecioGranelChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function SeccionCantidad({
  modoVenta,
  cantidadUnidad, setCantidadUnidad, stockActual,
  unidadDeVenta, inputCantidadGranel, handleCantidadGranelChange,
  inputPrecioGranel, handlePrecioGranelChange
}: SeccionCantidadProps) {

  // Si estamos en modo 'unidad', mostramos el input simple
  if (modoVenta === 'unidad') {
    return (
      <div className="flex flex-col gap-4 items-start justify-between md:flex-row">
        <Label className="text-2xl font-semibold text-green-900">Cantidad</Label>
        <Input
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
          className="w-full md:max-w-2/3 text-black"
        />
      </div>
    );
  }

  // Si estamos en modo 'granel', mostramos el doble input
  return (
    <div className="flex flex-col md:flex-row gap-4 w-full">
      {/* Input de Cantidad (Kg, Lt, etc.) */}
      <div className="flex flex-col gap-4 items-start justify-between md:flex-row w-full">
          <Label className="text-2xl font-semibold text-green-900">Cantidad ({unidadDeVenta})</Label>
          <Input
            type="number"
            value={inputCantidadGranel}
            onChange={handleCantidadGranelChange}
            step="0.01"
            className="w-full md:max-w-2/3 text-black"
          />
      </div>
      
      {/* Input de Precio ($) */}
      <div className="flex flex-col gap-4 items-start justify-between md:flex-row w-full">
          <Label className="text-2xl font-semibold text-green-900">Precio ($)</Label>
          <Input
            type="number"
            value={inputPrecioGranel}
            onChange={handlePrecioGranelChange}
            step="0.01"
            className="w-full md:max-w-2/3 text-black"
          />
      </div>
    </div>
  );
}