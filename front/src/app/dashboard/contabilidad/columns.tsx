"use client";

import { ColumnDef } from "@tanstack/react-table";
import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { formatDateArgentina } from "@/utils/formatDate";

// 1. (Recomendado) Define el tipo para un ítem individual dentro de una venta.
type ArticuloVendido = {
  id_articulo: number;
  nombre: string;
  cantidad: number;
  precio_unitario: number;
};

// 2. Esta es la modificación principal: enriquecemos la interfaz MovimientoAPI.
export interface MovimientoAPI {
  id: number;
  id_sesion_caja: number;
  id_venta_asociada?: number;
  id_usuario: number;
  tipo: string;
  concepto: string;
  monto: number;
  metodo_pago?: string;
  timestamp: string; // Corregido para coincidir con el backend
  usuario?: {
    nombre_usuario: string;
  };
  facturado: boolean; // Este campo parece estar duplicado, pero lo mantenemos si lo usas
  venta?: {
    id: number;
    facturada: boolean;
    descuento_total: number;
    datos_factura: string | null;
    tipo_comprobante_solicitado: string;
    cliente: {
      id: number;
      nombre_razon_social: string;
    } | null; // El cliente puede ser nulo (Consumidor Final)

    // ¡AÑADIMOS LA PROPIEDAD QUE FALTABA!
    articulos_vendidos: ArticuloVendido[];
  } | null; // La venta puede ser nula

  // Este campo parece ser redundante si ya tienes venta.tipo_comprobante_solicitado
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
    accessorFn: (row) => row.venta?.cliente?.id ?? "—",
    id: "id_cliente",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        className="px-0"
      >
        Cliente
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const idCliente = row.getValue("id_cliente") as number | string;
      const nombre = row.original.venta?.cliente?.nombre_razon_social ?? "Consumidor Final";

      return (
        <div className="flex flex-col">
          <span className="font-medium">{idCliente}</span>
          <span className="text-xs text-muted-foreground">{nombre}</span>
        </div>
      );
    },
    sortingFn: (rowA, rowB, columnId) => {
      // Sort por número si ambos son números, si no, por string normal
      const a = rowA.getValue(columnId);
      const b = rowB.getValue(columnId);

      if (typeof a === "number" && typeof b === "number") {
        return a - b;
      }

      return String(a).localeCompare(String(b));
    },
    filterFn: (row, id, filterValue) => {
      const idCliente = String(row.getValue(id) ?? "").toLowerCase();
      const nombreCliente = row.original.venta?.cliente?.nombre_razon_social?.toLowerCase() ?? "";
      const search = String(filterValue).toLowerCase();

      return idCliente.includes(search) || nombreCliente.includes(search);
    },
  },
  {
    accessorKey: "usuario",
    header: "Usuario",
    cell: ({ row }) => {
      const user = row.original.usuario;
      return user ? user.nombre_usuario : "—";
    },
  },
  {
    accessorKey: "descuento",
    header: "Descuento",
    cell: ({ row }) => {
      const descuento = row.original.venta?.descuento_total;
      if (!descuento || descuento <= 0) return "—";
      return (
        <span className="font-bold text-red-600">
          {new Intl.NumberFormat("es-AR", {
            style: "currency",
            currency: "ARS",
          }).format(descuento)}
        </span>
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
    accessorKey: "timestamp",
    header: "Fecha",
    cell: ({ row }) => {
      const fecha = row.getValue("timestamp") as string;
      return <span>{formatDateArgentina(fecha)}</span>;
    },
  },
];