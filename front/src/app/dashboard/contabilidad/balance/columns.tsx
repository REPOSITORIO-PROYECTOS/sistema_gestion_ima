"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { ArrowUpDown, ArrowDown, ArrowUp } from "lucide-react"

export type TipoOperacion = "Compra" | "Venta";
export type TipoUsuario = "Cliente" | "Proveedor";

export type Balance = {
  id: string;
  producto: string;
  cantidad: number;
  operacion: TipoOperacion;
  tipoUsuario: TipoUsuario;
  usuario: string;
  costo: number;
  fecha: Date;
};


export const columns: ColumnDef<Balance>[] = [

{
  accessorKey: "usuario",
  header: ({ column }) => {

    return (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Usuario
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    )
  },
},

{
  accessorKey: "tipoUsuario",         
  header: ({ column }) => {

    return (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Tipo
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    )
  },
},

{
  accessorKey: "operacion",     /* ACA SERIA IDEAL AGREGAR FLECHAS VERDES SI VENTA Y ROJO SI COMPRA */
  header: "Operación",
  cell: ({ row }) => {
    const operacion = row.getValue("operacion") as TipoOperacion;
    const esVenta = operacion.toLowerCase() === "venta";

    return (
      <div className="flex items-center gap-2 font-medium">
        {operacion}
        {esVenta ? (
          <ArrowUp className="h-4 w-4 text-green-600" />
        ) : (
          <ArrowDown className="h-4 w-4 text-red-600" />
        )}
      </div>
    );
  },
},   

{
  accessorKey: "producto",
  header: "Producto"
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