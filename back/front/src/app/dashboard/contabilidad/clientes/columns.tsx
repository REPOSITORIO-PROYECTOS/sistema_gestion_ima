"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge";

export type Cliente = {
  id: number;
  nombre_razon_social: string;
  cuit: string | null;
  condicion_iva: string;
  telefono: string;
};

export const columns: ColumnDef<Cliente>[] = [
  {
    accessorKey: "nombre_razon_social",
    header: "Razón Social",
  },
  {
    accessorKey: "cuit",
    header: "CUIT",
    cell: ({ row }) => {
      const cuit = row.getValue("cuit") as string | null;

      return cuit ? (
        <Badge className="bg-emerald-600 hover:bg-emerald-600 text-white text-md">
          {cuit}
        </Badge>
      ) : (
        <Badge className="bg-red-600 hover:bg-red-600 text-white text-md">
          Sin CUIT
        </Badge>
      );
    },
    filterFn: (row, id, value) => {
      const cuit = row.getValue(id) as string | null;
      if (value === "con") return !!cuit;
      if (value === "sin") return !cuit;
      return true;
    },
  },
  {
    accessorKey: "condicion_iva",
    header: "Condición IVA",
  },
  {
    accessorKey: "telefono",
    header: "Teléfono",
  },
];