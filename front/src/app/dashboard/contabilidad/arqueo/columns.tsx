"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";
import { formatDateArgentina } from "@/utils/formatDate";

// Este tipo debe coincidir con los datos reales
export type ArqueoCaja = {
  id_sesion: number;
  fecha_apertura: string;
  fecha_cierre: string | null;
  usuario_apertura: string;
  usuario_cierre: string;
  saldo_inicial: number;
  saldo_final_declarado: number | null;
  saldo_final_calculado: number | null;
  diferencia: number | null;
  estado: "ABIERTA" | "CERRADA";
  saldo_final_efectivo: number | null;
  saldo_final_transferencias: number | null;
  saldo_final_bancario: number | null;
};

export const columns: ColumnDef<ArqueoCaja>[] = [
  {
    accessorKey: "usuario_apertura",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Usuario Apertura
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "usuario_cierre",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Usuario Cierre
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "estado",
    header: "Estado",
    cell: ({ row }) => {
      const estado = row.getValue("estado") as string;
      const texto = estado === "ABIERTA" ? "Abierta" : "Cerrada";
      return (
        <span className={estado === "ABIERTA" ? "text-blue-600 font-medium" : "text-gray-700"}>
          {texto}
        </span>
      );
    },
  },
  {
    accessorKey: "fecha_apertura",
    header: "Apertura",
    cell: ({ row }) => {
      const fecha = row.getValue("fecha_apertura") as string;
      return <span>{formatDateArgentina(fecha)}</span>;
    },
  },
  {
    accessorKey: "fecha_cierre",
    header: "Cierre",
    cell: ({ row }) => {
      const fecha = row.getValue("fecha_cierre") as string | null;
      return (
        <span className={fecha ? "" : "text-blue-600 font-medium"}>
          {fecha ? formatDateArgentina(fecha) : "Caja abierta"}
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
    accessorKey: "saldo_final_declarado",
    header: "Saldo Declarado",
    cell: ({ row }) => {
      const valor = row.getValue("saldo_final_declarado") as number | null;
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
    accessorKey: "diferencia",
    header: "Diferencia",
    cell: ({ row }) => {
      const valor = row.getValue("diferencia") as number | null;
      const formato = formatCurrency(valor);
      return (
        <span className={valor === 0 ? "text-green-600" : "text-red-600"}>
          {valor! > 0 ? "+" : ""}
          {formato}
        </span>
      );
    },
  },
  {
    accessorKey: "saldo_final_efectivo",
    header: "Efectivo",
    cell: ({ row }) => {
      const valor = row.getValue("saldo_final_efectivo") as number | null;
      return formatCurrency(valor);
    },
  },
  {
    accessorKey: "saldo_final_transferencias",
    header: "Transferencias",
    cell: ({ row }) => {
      const valor = row.getValue("saldo_final_transferencias") as number | null;
      return formatCurrency(valor);
    },
  },
  {
    accessorKey: "saldo_final_bancario",
    header: "Bancario",
    cell: ({ row }) => {
      const valor = row.getValue("saldo_final_bancario") as number | null;
      return formatCurrency(valor);
    },
  },
];

// Formatea números como moneda ARS
function formatCurrency(value: number | null) {
  if (value === null) return "-";
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
  }).format(value);
}