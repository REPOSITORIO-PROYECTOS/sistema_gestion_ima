"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { ArrowUpDown } from "lucide-react"

export type ProductosProveedor = {
  id: string;
  producto: string;
  proveedor: string;
  cantidad: number;
  costo: number;
  fecha: Date;
};


export const columns: ColumnDef<ProductosProveedor>[] = [

{
  accessorKey: "producto",
  header: ({ column }) => {

    return (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Producto
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    )
  },
},

{
  accessorKey: "proveedor",
  header: ({ column }) => {

    return (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Proveedor
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    )
  },
},

{
  accessorKey: "cantidad",
  header: "Cantidad",
},

{
  accessorKey: "fecha",
  header: "Fecha",
  cell: ({ row }) => {
    const fecha = row.getValue("fecha") as Date;
    const fechaFormateada = new Date(fecha).toLocaleString("es-AR", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });

    return <div className="font-medium">{fechaFormateada}</div>;
  }
},

{
  accessorKey: "costo",
  header: () => <div className="text-right">Costo</div>,
  cell: ({ row }) => {
    const amount = parseFloat(row.getValue("costo"))
    const formatted = new Intl.NumberFormat("es-AR", {
      style: "currency",
      currency: "ARS",
    }).format(amount)

    return <div className="text-right font-semibold">{formatted}</div>
  }
},

]