"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LegacyRef, KeyboardEvent } from "react"
import { handleEnterAvanzar, VENTAS_CAMPOS, focusVentasCampo } from "@/lib/ventas-form-flow"

interface SeccionCantidadProps {
  cantidadInputRef: LegacyRef<HTMLInputElement>;
  modoVenta: 'unidad' | 'granel' | 'precio_manual';
  cantidadUnidad: number;
  setCantidadUnidad: (value: number) => void;
  stockActual: number;
  unidadDeVenta: string;
  inputCantidadGranel: string;
  handleCantidadGranelChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  inputPrecioGranel: string;
  handlePrecioGranelChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onEnterConfirm?: () => void;
}

const inputClass = "w-full text-black text-lg min-h-12 touch-manipulation";

export function SeccionCantidad({
  cantidadInputRef,
  modoVenta,
  cantidadUnidad, setCantidadUnidad, stockActual: _stockActual,
  unidadDeVenta, inputCantidadGranel, handleCantidadGranelChange,
  inputPrecioGranel, handlePrecioGranelChange,
  onEnterConfirm,
}: SeccionCantidadProps) {
  const limiteStock = undefined;

  const onCantidadKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!onEnterConfirm) return;
    handleEnterAvanzar(e, onEnterConfirm);
  };

  const onGranelCantidadKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    focusVentasCampo(VENTAS_CAMPOS.precioGranel);
  };

  const onGranelPrecioKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!onEnterConfirm) return;
    handleEnterAvanzar(e, onEnterConfirm);
  };

  if (modoVenta === 'precio_manual') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-center">
        <Label htmlFor={VENTAS_CAMPOS.precioManual} className="text-xl font-semibold text-green-900 md:text-right">
          Precio de venta
        </Label>
        <div className="md:col-span-2">
          <Input
            id={VENTAS_CAMPOS.precioManual}
            ref={cantidadInputRef}
            type="number"
            inputMode="decimal"
            min={0.01}
            step="0.01"
            placeholder="Ingrese el importe"
            value={inputPrecioGranel}
            onChange={handlePrecioGranelChange}
            onKeyDown={onCantidadKeyDown}
            className={inputClass}
            enterKeyHint="done"
          />
        </div>
      </div>
    );
  }

  if (modoVenta === 'unidad') {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-center">
        <Label htmlFor={VENTAS_CAMPOS.cantidadUnidad} className="text-xl font-semibold text-green-900 md:text-right">
          Cantidad
        </Label>
        <div className="md:col-span-2">
          <Input
            id={VENTAS_CAMPOS.cantidadUnidad}
            ref={cantidadInputRef}
            type="number"
            inputMode="numeric"
            enterKeyHint="done"
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
            onKeyDown={onCantidadKeyDown}
            className={inputClass}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-center">
      <Label className="text-xl font-semibold text-green-900 md:text-right">
        Cantidad / Precio
      </Label>
      <div className="md:col-span-2 grid grid-cols-2 gap-x-3 gap-y-2">
        <div className="flex flex-col gap-2">
          <Label htmlFor={VENTAS_CAMPOS.cantidadGranel} className="text-sm text-muted-foreground">
            ({unidadDeVenta})
          </Label>
          <Input
            id={VENTAS_CAMPOS.cantidadGranel}
            ref={cantidadInputRef}
            type="number"
            inputMode="decimal"
            enterKeyHint="next"
            value={inputCantidadGranel}
            onChange={handleCantidadGranelChange}
            onKeyDown={onGranelCantidadKeyDown}
            step="0.01"
            className={inputClass}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor={VENTAS_CAMPOS.precioGranel} className="text-sm text-muted-foreground">
            ($)
          </Label>
          <Input
            id={VENTAS_CAMPOS.precioGranel}
            type="number"
            inputMode="decimal"
            enterKeyHint="done"
            value={inputPrecioGranel}
            onChange={handlePrecioGranelChange}
            onKeyDown={onGranelPrecioKeyDown}
            step="0.01"
            className={inputClass}
          />
        </div>
      </div>
    </div>
  );
}
