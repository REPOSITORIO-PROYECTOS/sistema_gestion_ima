"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { ArrowUpDown } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
  /* DialogTrigger, */
} from "@/components/ui/dialog"
import AddStockForm from "./StockForm"

export type Stock = {
  id: string;
  producto: string;
  cantidad: number;
  costo: number;
  ubicacion: string;
  fecha: Date;
};

export const columns: ColumnDef<Stock>[] = [
  {
    accessorKey: "producto",
    header: ({ column }) => (
      <Button variant="ghost" onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}>
        Nombre de Producto
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
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
    },
  },
  {
    accessorKey: "ubicacion",
    header: "Ubicación",
  },
  {
    accessorKey: "costo",
    header: () => <div className="text-right">Costo</div>,
    cell: ({ row }) => {
      const amount = parseFloat(row.getValue("costo"));
      const formatted = new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
      }).format(amount);

      return <div className="text-right font-semibold">{formatted}</div>;
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {

      const stock = row.original;

      return (
        <Dialog>

          <DialogTrigger asChild>
            <Button variant="secondary">Editar</Button>
          </DialogTrigger>

          <DialogContent className="sm:max-w-lg">

            <DialogHeader>
              <DialogTitle>Editar Producto: {stock.producto}</DialogTitle>
              <DialogDescription>Modifica los datos necesarios</DialogDescription>
            </DialogHeader>

            {/* Componente Form para Stock - mode="edit", que envía metodo PUT */}
            <AddStockForm
              mode="edit"
              initialData={{
                id: stock.id,
                nombre: stock.producto,
                cantidad: stock.cantidad,
                ubicacion: stock.ubicacion,
                costoUnitario: stock.costo,
              }}
            />

          </DialogContent>

        </Dialog>
      );
    },
  }
];
