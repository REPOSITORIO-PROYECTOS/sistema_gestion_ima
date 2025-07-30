// app/dashboard/contabilidad/libro-mayor/columns.tsx
"use client";

// CAMBIO: Importamos 'Row' desde la librería de la tabla.
import { type ColumnDef, type Row } from "@tanstack/react-table";
import { useMovimientosCajaStore } from "@/lib/useMovimientosCajaStore";
import type { MovimientoContable } from "@/types/contabilidad.types";

const formatFecha = (fechaISO: string) => new Date(fechaISO).toLocaleString();

// Componente para la celda de selección (ya estaba bien)
const SelectCellComponent = ({ row }: { row: Row<MovimientoContable> }) => { // <-- CAMBIO AQUÍ
  const { seleccionados, toggleSeleccion } = useMovimientosCajaStore();
  const movimiento: MovimientoContable = row.original;
  const isPendiente = movimiento.tipo === 'VENTA' && movimiento.venta && !movimiento.venta.facturada;

  if (!isPendiente) {
    return null;
  }

  return (
    <div className="flex items-center justify-center">
      <input
        type="checkbox"
        checked={seleccionados.includes(movimiento.id)}
        onChange={() => toggleSeleccion(movimiento.id)}
        className="h-4 w-4"
      />
    </div>
  );
};

// Se corrige el tipo de la prop 'row' en varios lugares
export const columns: ColumnDef<MovimientoContable>[] = [
  {
    id: "select",
    header: () => null,
    cell: SelectCellComponent,
  },
  {
    accessorKey: "timestamp",
    header: "Fecha",
    cell: ({ row }) => formatFecha(row.getValue("timestamp")),
  },
  {
    accessorKey: "tipo",
    header: "Tipo",
  },
  {
    accessorKey: "concepto",
    header: "Concepto",
  },
  {
    id: "cliente",
    header: "Cliente",
    cell: ({ row }) => row.original.venta?.cliente?.nombre_razon_social || "N/A",
  },
  {
    accessorKey: "monto",
    header: () => <div className="text-right">Monto</div>,
    cell: ({ row }) => {
      const amount = parseFloat(row.getValue("monto"));
      const formatted = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS" }).format(amount);
      return <div className="text-right font-medium">{formatted}</div>;
    },
  },
  {
    id: "estado",
    header: "Estado Factura",
    cell: ({ row }) => {
      const movimiento = row.original;
      if (movimiento.tipo !== 'VENTA' || !movimiento.venta) return null;
      const isFacturada = movimiento.venta.facturada;
      return (
        <span className={`px-2 py-1 rounded text-xs ${isFacturada ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
          {isFacturada ? 'Facturado' : 'Pendiente'}
        </span>
      );
    },
  },
];