"use client"

// --- PASO 1: AÑADIR 'export' AL TIPO ---
export type ItemParaResumen = {
    descripcion: string;
    cantidad: number;
    precio_unitario_antiguo: number;
    precio_unitario_nuevo: number;
    subtotal_nuevo: number;
};

interface ResumenItemsProps {
  items: ItemParaResumen[];
  totalFinal: number;
}

// --- PASO 2: AÑADIR 'export' A LA FUNCIÓN ---
export function ResumenItemsModal({ items, totalFinal }: ResumenItemsProps) {
  // Si no hay items, no mostramos nada para no ocupar espacio
  if (!items || items.length === 0) {
    return null;
  }

  return (
    <div className="grid gap-3 pt-4">
      <h4 className="font-semibold text-md">Detalle de la Operación (Precios Actualizados):</h4>
      <div className="max-h-48 overflow-y-auto rounded-md border bg-muted/50 p-2 text-sm">
        {items.map((item, index) => (
          <div key={index} className="flex justify-between items-center gap-2 border-b py-1.5 last:border-b-0">
            {/* Lado izquierdo: Descripción y cantidad */}
            <div className="flex flex-col flex-1 truncate">
              <span className="font-medium truncate">{item.descripcion}</span>
              <span className="text-xs text-muted-foreground">Cantidad: {item.cantidad}</span>
            </div>
            {/* Lado derecho: Precios y subtotal */}
            <div className="flex flex-col items-end font-mono">
              <span className="text-xs text-muted-foreground line-through">
                ${item.precio_unitario_antiguo.toFixed(2)}
              </span>
              <span>${item.subtotal_nuevo.toFixed(2)}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between items-center text-lg font-bold border-t pt-2 mt-2">
        <span>Total a la fecha:</span>
        <span className="font-mono">${totalFinal.toFixed(2)}</span>
      </div>
    </div>
  );
}