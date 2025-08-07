"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { useAuthStore } from "@/lib/authStore"

// ==========================================================
// === CORRECCIÓN 1: Actualizamos las props que el componente recibe ===
// ==========================================================
interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  // Hacemos que la prop sea opcional para que la tabla siga funcionando en
  // otras partes de la app que no necesiten esta lógica.
  onActionComplete?: () => void;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  onActionComplete, // <-- La recibimos como prop
}: DataTableProps<TData, TValue>) {

    const [sorting, setSorting] = useState<SortingState>([])
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
    const token = useAuthStore((state) => state.token);

    // Sincronizador de Proveedores
    const handleSyncProveedores = async () => {

        toast("Sincronizando proveedores... Por favor espera");
    
            try {
                const response = await fetch("https://sistema-ima.sistemataup.online/api/sincronizar/proveedores", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({}),
                });
    
                if (!response.ok) throw new Error("Fallo en la respuesta del servidor");

                toast.success("✅ Proveedores sincronizados!");

            } catch (error) {
                console.error("Error al sincronizar proveedores:", error);
                toast.error("❌ Error al sincronizar proveedores");
            }
    };


    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        onSortingChange: setSorting,
        getSortedRowModel: getSortedRowModel(),
        onColumnFiltersChange: setColumnFilters,
        getFilteredRowModel: getFilteredRowModel(),
        state: {
            sorting,
            columnFilters,
        },
        // ========================================================================
        // === CORRECCIÓN 2: Pasamos la función a la metadata de la tabla ===
        // ========================================================================
        // `meta` es una propiedad especial de TanStack Table para pasar datos
        // y funciones a cualquier parte de la tabla (como a las celdas).
        meta: {
            onActionComplete: onActionComplete,
        }
    })

    return (
    <div>
        <h2 className="text-2xl font-semibold text-green-950 text-center md:hidden my-4">Tabla de Proveedores</h2>
        <div className="flex flex-col md:flex-row-reverse justify-between gap-2 pb-4">
            <div className="flex flex-col sm:flex-row justify-between items-center gap-2 w-full">
                <Input
                    placeholder="Buscar por razón social"
                    value={(table.getColumn("nombre_razon_social")?.getFilterValue() as string) ?? ""}
                    onChange={(event) =>
                        table.getColumn("nombre_razon_social")?.setFilterValue(event.target.value)
                    }
                    className="w-full sm:w-1/2 md:max-w-1/4"
                />
                <Button variant="outline" className="w-full sm:w-1/3 md:w-1/4" onClick={handleSyncProveedores}>
                    Sincronizar Proveedores
                </Button>
            </div>
        </div>

        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    {table.getHeaderGroups().map((headerGroup) => (
                        <TableRow key={headerGroup.id}>
                            {headerGroup.headers.map((header) => (
                                <TableHead key={header.id}>
                                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                                </TableHead>
                            ))}
                        </TableRow>
                    ))}
                </TableHeader>
                <TableBody>
                    {table.getRowModel().rows?.length ? (
                        table.getRowModel().rows.map((row) => (
                            <TableRow key={row.id} data-state={row.getIsSelected() && "selected"}>
                                {row.getVisibleCells().map((cell) => (
                                    <TableCell key={cell.id} className="px-4">
                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))
                    ) : (
                        <TableRow>
                            <TableCell colSpan={columns.length} className="h-24 text-center">
                                No hay resultados.
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>

        <div className="flex flex-col sm:flex-row justify-between items-center m-2">
            <Select onValueChange={(value) => table.setPageSize(+value)}>
                <SelectTrigger className="w-[100px] m-2 cursor-pointer">
                    <SelectValue placeholder="10 filas" />
                </SelectTrigger>
                <SelectContent>
                    <SelectGroup>
                        <SelectLabel>Filas por Página</SelectLabel>
                        <SelectItem value="10">10</SelectItem>
                        <SelectItem value="20">20</SelectItem>
                        <SelectItem value="30">30</SelectItem>
                        <SelectItem value="40">40</SelectItem>
                        <SelectItem value="50">50</SelectItem>
                    </SelectGroup>
                </SelectContent>
            </Select>
            <div className="flex items-center justify-end space-x-2 py-4 mx-2">
                <Button variant="outline" size="sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>
                    Anterior
                </Button>
                <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>
                    Siguiente
                </Button>
            </div>
        </div>
    </div>
    )
}