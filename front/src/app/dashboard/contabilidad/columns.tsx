"use client";

import { ColumnDef } from "@tanstack/react-table";
import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export interface MovimientoAPI {
  id: number;
  id_sesion_caja: number;
  id_venta_asociada?: number;
  id_usuario: number;
  tipo: string;
  concepto: string;
  monto: number;
  metodo_pago?: string;
  fecha_hora: string;
  facturado: boolean;
}

export const columns: ColumnDef<MovimientoAPI>[] = [
  {
    accessorKey: "tipo",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting()}>
        Tipo de Movimiento
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const tipo = row.getValue("tipo") as string;
      let variant: "default" | "secondary" | "destructive" | "outline" = "default";
      let customClass = "";

      switch (tipo) {
        case "VENTA":
          customClass = "bg-green-900 text-white";
          break;
        case "APERTURA":
          customClass = "bg-sky-500 text-white";
          break;
        case "EGRESO":
          customClass = "bg-red-800 text-white";
          break;
        default:
          variant = "secondary";
      }

      return (
        <Badge className={customClass} variant={variant}>
          {tipo}
        </Badge>
      );
    },
  },
  {
    accessorKey: "concepto",
    header: "Concepto",
  },
  {
    accessorKey: "monto",
    header: "Monto",
    cell: ({ row }) => {
      const value = row.getValue("monto") as number;
      return new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
      }).format(value);
    },
  },
  {
    accessorKey: "metodo_pago",
    header: "Método de Pago",
  },
  {
    accessorKey: "fecha_hora",
    header: "Fecha",
    cell: ({ row }) => {
      const fecha = new Date(row.getValue("fecha_hora") as string);
      return fecha.toLocaleString("es-AR");
    },
  },
  {
    accessorKey: "facturado",
    header: "Facturado",
    cell: ({ row }) => (row.getValue("facturado") ? "Sí" : "No"),
  },
];