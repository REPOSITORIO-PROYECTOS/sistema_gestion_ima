"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";
import { ProveedorExcelUpload } from "./ModalExcelUploader";

// Importamos el tipo RowData para la declaración del módulo, requerido por TypeScript
import type { RowData } from '@tanstack/react-table';

export type Proveedor = {
  id: number;
  nombre_razon_social: string;
  nombre_fantasia?: string;
  cuit?: string;
  condicion_iva: string;
  email?: string;
  telefono?: string;
  direccion?: string;
  notas?: string;
};

export const columns: ColumnDef<Proveedor>[] = [
  {
    accessorKey: "nombre_razon_social",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Razón Social
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "cuit",
    header: "CUIT",
  },
  {
    id: "acciones",
    header: () => <div className="text-right">Acciones</div>,
    cell: ({ row, table }) => {
      const proveedor = row.original;
      const onActionComplete = table.options.meta?.onActionComplete as () => void;

      return (
        <div className="text-right">
          <ProveedorExcelUpload 
            proveedor={proveedor} 
            onUploadComplete={onActionComplete} 
          />
        </div>
      );
    },
  },
];

// Extendemos la definición de tipos de TanStack Table
declare module '@tanstack/react-table' {
  // =========================================================================
  // === CORRECCIÓN FINAL: Deshabilitamos la regla de ESLint para esta línea ===
  // =========================================================================
  // Le decimos a ESLint que ignore el error de "variable no usada" para 'TData',
  // porque TypeScript nos obliga a declararla aquí.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface TableMeta<TData extends RowData> {
    onActionComplete?: () => void
  }
}