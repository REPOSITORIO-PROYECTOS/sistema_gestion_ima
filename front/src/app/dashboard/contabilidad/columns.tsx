"use client";

import { ColumnDef } from "@tanstack/react-table";
import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";

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
  venta?: {
    id: number;
    facturada: boolean;
    datos_factura: string | null;
    tipo_comprobante_solicitado: string;
    cliente: {
      id: number;
      nombre_razon_social: string;
    };
  };
  tipo_comprobante: "comprobante" | "remito" | "presupuesto" | "factura";
}

export const columns: ColumnDef<MovimientoAPI>[] = [
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllPageRowsSelected()}
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label="Seleccionar todo"
        className="cursor-pointer"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label="Seleccionar fila"
        className="cursor-pointer"
      />
    ),
    enableSorting: false,
    enableHiding: false,
  },
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
          customClass = "ml-6 bg-green-900 text-white";
          break;
        case "APERTURA":
          customClass = "ml-6 bg-sky-500 text-white";
          break;
        case "EGRESO":
          customClass = "ml-6 bg-red-800 text-white";
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
    accessorFn: (row) => row.venta?.tipo_comprobante_solicitado ?? "—",
    id: "tipo_comprobante_solicitado",
    header: "Tipo Comprobante",
    cell: ({ row }) => {
      const rawValue = row.getValue("tipo_comprobante_solicitado") as string;
      const displayValue = rawValue.toLowerCase() === "recibo" ? "comprobante" : rawValue;

      return (
        <Badge variant="secondary" className="ml-4">
          {displayValue.toUpperCase()}
        </Badge>
      );
    },
  },
  {
    accessorFn: row => row.venta?.facturada, 
    id: "facturado",
    header: "Facturado",
    filterFn: (row, id, value) => {
      const rowValue = row.getValue(id);
      if (value === "true") return rowValue === true;
      if (value === "false") return rowValue === false;
      return true;
    },
    cell: ({ row }) => {
      const value = row.getValue("facturado") as boolean;
      const badgeClass = value ? "ml-6 bg-green-600 text-white" : "ml-6 bg-red-600 text-white";
      const label = value ? "Sí" : "No";

      return (
        <Badge className={badgeClass} variant="default">
          {label}
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
];