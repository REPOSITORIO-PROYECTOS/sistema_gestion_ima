"use client"

import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import { ArrowUpDown } from "lucide-react";
import { ProveedorExcelUpload } from "./ModalExcelUploader";

export type Proveedor = {
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
        Razón Social <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
  },
  {
    accessorKey: "nombre_fantasia",
    header: "Nombre Fantasía",
  },
  {
    accessorKey: "cuit",
    header: "CUIT",
  },
  {
    accessorKey: "condicion_iva",
    header: "Condición IVA",
  },
  {
    accessorKey: "email",
    header: "Email",
  },
  {
    accessorKey: "telefono",
    header: "Teléfono",
  },
  {
    accessorKey: "direccion",
    header: "Dirección",
  },
  {
    id: "acciones",
    header: "Acciones",
    cell: ({ row }) => {
      const proveedor = row.original;
      return <ProveedorExcelUpload proveedor={proveedor} />;
    },
  },
];
