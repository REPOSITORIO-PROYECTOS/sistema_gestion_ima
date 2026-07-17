"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import type { MovimientoAPI } from "./columns";

interface DetalleVentaModalProps {
  movimiento: MovimientoAPI | null;
  isOpen: boolean;
  onClose: () => void;
}

const formatearMoneda = (valor: number): string =>
  new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
  }).format(valor);

export function DetalleVentaModal({ movimiento, isOpen, onClose }: DetalleVentaModalProps) {
  const venta = movimiento?.venta ?? null;
  const items = venta?.items ?? [];

  const subtotalItems = items.reduce((acc, item) => acc + item.subtotal, 0);
  const nombreCliente = venta?.cliente?.nombre_razon_social ?? "Consumidor Final";

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            Detalle de la venta {venta ? `#${venta.id}` : ""}
          </DialogTitle>
          <DialogDescription>
            Cliente: {nombreCliente}
          </DialogDescription>
        </DialogHeader>

        {/* Resumen del movimiento */}
        <div className="flex flex-wrap gap-2 text-sm">
          <Badge variant="secondary">
            Método: {movimiento?.metodo_pago ?? "—"}
          </Badge>
          <Badge variant="secondary">
            Comprobante: {venta?.tipo_comprobante_solicitado ?? "—"}
          </Badge>
          <Badge className={venta?.facturada ? "bg-green-600 text-white" : "bg-red-600 text-white"}>
            {venta?.facturada ? "Facturada" : "No facturada"}
          </Badge>
          {movimiento?.estado === "ANULADO" && (
            <Badge variant="outline" className="border-red-500 text-red-600">
              ANULADO
            </Badge>
          )}
        </div>

        {/* Tabla de items */}
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">
            Esta venta no tiene ítems registrados.
          </p>
        ) : (
          <div className="max-h-72 overflow-y-auto rounded-md border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 sticky top-0">
                <tr className="text-left">
                  <th className="p-2">Producto</th>
                  <th className="p-2 text-right">Cant.</th>
                  <th className="p-2 text-right">P. Unitario</th>
                  <th className="p-2 text-right">Desc.</th>
                  <th className="p-2 text-right">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <tr key={index} className="border-t">
                    <td className="p-2">{item.descripcion}</td>
                    <td className="p-2 text-right font-mono">{item.cantidad}</td>
                    <td className="p-2 text-right font-mono">
                      {formatearMoneda(item.precio_unitario)}
                    </td>
                    <td className="p-2 text-right font-mono">
                      {item.descuento_aplicado > 0
                        ? formatearMoneda(item.descuento_aplicado)
                        : "—"}
                    </td>
                    <td className="p-2 text-right font-mono">
                      {formatearMoneda(item.subtotal)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Totales */}
        <div className="flex flex-col gap-1 border-t pt-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Subtotal ítems</span>
            <span className="font-mono">{formatearMoneda(subtotalItems)}</span>
          </div>
          {venta && venta.descuento_total > 0 && (
            <div className="flex justify-between text-red-600">
              <span>Descuento total</span>
              <span className="font-mono">-{formatearMoneda(venta.descuento_total)}</span>
            </div>
          )}
          <div className="flex justify-between text-lg font-bold border-t pt-2 mt-1">
            <span>Total del movimiento</span>
            <span className="font-mono">{formatearMoneda(movimiento?.monto ?? 0)}</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
