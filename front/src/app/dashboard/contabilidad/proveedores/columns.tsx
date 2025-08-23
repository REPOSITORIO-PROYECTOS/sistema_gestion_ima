"use client";

import { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { ArrowUpDown, MoreHorizontal, FileCog } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// Este es el tipo de dato para una fila de la tabla.
// Asegúrate de que coincida con lo que devuelve tu API.
export type Proveedor = {
  id: number;
  nombre_razon_social: string;
  cuit: string | null;
  condicion_iva: string;
  activo: boolean;
};

export const columns: ColumnDef<Proveedor>[] = [
  {
    accessorKey: "nombre_razon_social",
    header: ({ column }) => {
      return (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          Razón Social
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      );
    },
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
    accessorKey: "activo",
    header: "Estado",
    cell: ({ row }) => {
      const activo = row.getValue("activo");
      return activo ? "Activo" : "Inactivo";
    },
  },
  // --- INICIO DE LA COLUMNA CLAVE ---
  // Esta es la nueva columna que añade la funcionalidad que necesitas.
  {
    id: "actions",
    cell: ({ row }) => {
      const proveedor = row.original;

      return (
        <div className="text-right">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Abrir menú</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Acciones</DropdownMenuLabel>
              {/* 
                Este es el enlace que te lleva a la página de detalles/configuración 
                del proveedor, usando el ID de la fila actual.
              */}
              <Link href={`/dashboard/contabilidad/proveedores/${proveedor.id}`} passHref>
                <DropdownMenuItem className="cursor-pointer">
                  <FileCog className="mr-2 h-4 w-4" />
                  Gestionar Plantilla y Precios
                </DropdownMenuItem>
              </Link>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      );
    },
  },
  // --- FIN DE LA COLUMNA CLAVE ---
];