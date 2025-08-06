"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";

export interface ProductoAPI {
  id: number;
  descripcion: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
  codigo_interno: string;
  ubicacion: string;
}

export const columns: ColumnDef<ProductoAPI>[] = [
  {
    accessorKey: "descripcion",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Nombre de Producto
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
    {
    accessorKey: "codigo_interno",
    header: "Código de Barras",
    cell: ({ row }) => {
      const codigo = row.getValue("codigo_interno") as string;
      return <div className="font-mono text-sm">{codigo}</div>;
    }
  },
  {
    accessorKey: "precio_venta",
    header: "Precio de Venta al Público",
    cell: ({ row }) => {
      const value = row.getValue("precio_venta") as number;
      const formatted = new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
      }).format(value);
      return <div className="font-medium">{formatted}</div>;
    },
  },
  {
    accessorKey: "venta_negocio",
    header: "Precio de Venta a Clientes",
    cell: ({ row }) => {
      const value = row.getValue("venta_negocio") as number;
      const formatted = new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
      }).format(value);
      return <div className="font-medium">{formatted}</div>;
    },
  },
  {
    accessorKey: "stock_actual",
    header: "Stock",
    cell: ({ row }) => {
      const stock = row.getValue("stock_actual") as number;
      return <div className="font-medium">{stock}</div>;
    },
  },
  {
    accessorKey: "ubicacion",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Ubicación del Producto
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const codigo = row.getValue("ubicacion") as string;
      return <div className="font-mono text-sm">{codigo}</div>;
    }
  }
];