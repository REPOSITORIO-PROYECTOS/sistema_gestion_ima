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
import { toast } from "sonner";
import { useAuthStore } from "@/lib/authStore"

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
}

export function DataTable<TData, TValue>({
  columns,
  data,
}: DataTableProps<TData, TValue>) {

    const [sorting, setSorting] = useState<SortingState>([])
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
    const token = useAuthStore((state) => state.token);

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
    })

    /* Sync tabla de articulos en backend */
    const handleSyncArticulos = async () => {
        
        toast("Sincronizando artículos... Por favor espera");

        try {
            const response = await fetch("https://sistema-ima.sistemataup.online/api/sincronizar/articulos", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({}),
            });

            if (!response.ok) throw new Error("Fallo en la respuesta del servidor");

            toast.success("Artículos sincronizados ✅");
            
        } catch (error) {
            console.error("Error al sincronizar artículos:", error);
            toast.error("Error al sincronizar artículos ❌");
        }
    };

    return (

        <div>

            {/* Headers de la Tabla */}
            <div className="flex flex-col md:flex-row justify-between items-center gap-4 pb-4">

                <h2 className="block sm:hidden text-start text-xl font-semibold text-green-950 my-4">Sección de Stock</h2>

                {/* Input de Búsqueda por Producto */}
                <Input
                    placeholder="Filtrar por producto"
                    value={(table.getColumn("descripcion")?.getFilterValue() as string) ?? ""}
                    onChange={(event) =>
                        table.getColumn("descripcion")?.setFilterValue(event.target.value)
                    }
                    className="w-full md:w-1/6"
                />

                {/* Input de Búsqueda por Código de Barras */}
                <Input
                    placeholder="Filtrar por código de barras"
                    value={(table.getColumn("codigos")?.getFilterValue() as string) ?? ""}
                    onChange={(event) =>
                        table.getColumn("codigos")?.setFilterValue(event.target.value)
                    }
                    className="w-full md:w-1/6"
                />

                {/* Botones para sincronización */}
                <div className="flex gap-2 w-full md:w-1/3 md:flex-row flex-col">
                    <Button variant="outline" onClick={handleSyncArticulos}>Sincronizar Artículos</Button>
                </div>

                <div className="flex justify-center items-center w-full md:w-1/3 p-4 text-sm bg-yellow-100 border border-yellow-300 rounded-lg text-yellow-800">
                    Para agregar nuevos productos dirigirse a la sección de contabilidad / proveedores.
                </div>

            </div>

            {/* Tabla */}
            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                    {table.getHeaderGroups().map((headerGroup) => (

                        <TableRow key={headerGroup.id}>
                        {headerGroup.headers.map((header) => {
                            return (
                            <TableHead key={header.id}>
                                {header.isPlaceholder
                                ? null
                                : flexRender(
                                    header.column.columnDef.header,
                                    header.getContext()
                                    )}
                            </TableHead>
                            )
                        })}
                        </TableRow>
                    ))}
                    </TableHeader>

                    <TableBody>
                    {table.getRowModel().rows?.length ? (

                        table.getRowModel().rows.map((row) => (

                        <TableRow key={row.id} data-state={row.getIsSelected() && "selected"}>

                            {/* Filas Tabla */}
                            {row.getVisibleCells().map((cell) => (
                            <TableCell key={cell.id} className="px-6">
                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </TableCell>
                            ))}

                        </TableRow>
                        ))
                    ) : (
                        <TableRow>
                        <TableCell colSpan={columns.length} className="h-24 text-center">
                            No hay resultados que coincidan con la búsqueda.
                        </TableCell>
                        </TableRow>
                    )}
                    </TableBody>
                </Table>

                {/* Footer Tabla */}
                <div className="flex flex-col sm:flex-row justify-between items-center m-2">

                    {/* Control de Filas por Página */}
                    <Select onValueChange={(value) => {  table.setPageSize(+value) }}>
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

                    {/* Controles de Paginación */}
                    <div className="flex items-center justify-end space-x-2 py-4 mx-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => table.previousPage()}
                            disabled={!table.getCanPreviousPage()}
                        >
                        Anterior
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => table.nextPage()}
                            disabled={!table.getCanNextPage()}
                        >
                        Siguiente
                        </Button>
                    </div>

                </div>
            </div>
        </div>
    )
}