// columns.tsx
"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";

// Este tipo debe coincidir con los datos reales
export type ArqueoCaja = {
  id_sesion: number;
  fecha_apertura: string;
  fecha_cierre: string | null;
  usuario_apertura: string;
  saldo_inicial: number;
  saldo_final_declarado: number | null;
  saldo_final_calculado: number | null;
  diferencia: number | null;
};

export const columns: ColumnDef<ArqueoCaja>[] = [
  {
    accessorKey: "usuario_apertura",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Usuario
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "fecha_apertura",
    header: "Apertura",
    cell: ({ row }) => {
      const fecha = row.getValue("fecha_apertura") as string;
      const formateada = new Date(fecha).toLocaleString("es-AR");
      return <span>{formateada}</span>;
    },
  },
  {
    accessorKey: "fecha_cierre",
    header: "Cierre",
    cell: ({ row }) => {
      const fecha = row.getValue("fecha_cierre") as string | null;
      return (
        <span>
          {fecha ? new Date(fecha).toLocaleString("es-AR") : "Caja abierta"}
        </span>
      );
    },
  },
  {
    accessorKey: "saldo_inicial",
    header: "Saldo Inicial",
    cell: ({ row }) => {
      const valor = row.getValue("saldo_inicial") as number | null;
      return formatCurrency(valor);
    },
  },
  {
    accessorKey: "saldo_final_calculado",
    header: "Saldo Calculado",
    cell: ({ row }) => {
      const valor = row.getValue("saldo_final_calculado") as number | null;
      return formatCurrency(valor);
    },
  },
  {
    accessorKey: "saldo_final_declarado",
    header: "Saldo Declarado",
    cell: ({ row }) => {
      const valor = row.getValue("saldo_final_declarado") as number | null;
      return formatCurrency(valor);
    },
  },
  {
    accessorKey: "diferencia",
    header: "Diferencia",
    cell: ({ row }) => {
      const valor = row.getValue("diferencia") as number | null;
      const formato = formatCurrency(valor);
      return <span className={valor === 0 ? "text-green-600" : "text-red-600"}>{formato}</span>;
    },
  },
];

function formatCurrency(value: number | null) {
  if (value === null) return "-";
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
  }).format(value);
}