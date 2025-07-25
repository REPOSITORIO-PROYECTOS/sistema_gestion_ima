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
import type { Row } from "@tanstack/react-table";
import type { ArqueoCaja } from "./columns";

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
    /* const [currentStatus, setCurrentStatus] = useState("all") */

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

    return (

    <div>

        <h2 className="text-2xl font-semibold text-green-950 text-center md:hidden my-4">Arqueo de Caja</h2>

        {/* Inputs de Filtrado */}
        <div className="flex flex-col sm:flex-row justify-between gap-2 pb-4">

            {/* Input de Búsqueda por cliente */}
            <Input
                placeholder="Filtrar por Usuario"
                value={(table.getColumn("usuario_apertura")?.getFilterValue() as string) ?? ""}
                onChange={(event) => table.getColumn("usuario_apertura")?.setFilterValue(event.target.value)}
                className="w-full sm:w-1/2 md:max-w-1/4"
            />

            {/* Input de Seleccion por status */}
            <Select
                onValueChange={(value) =>
                    table.getColumn("estado")?.setFilterValue(value === "all" ? undefined : value)
                }
                >
                <SelectTrigger className="w-full sm:w-1/2 md:max-w-1/4 cursor-pointer">
                    <SelectValue placeholder="Filtrar por Estado" />
                </SelectTrigger>
                <SelectContent>
                    <SelectGroup>
                    <SelectLabel>Estado</SelectLabel>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="ABIERTA">Abierta</SelectItem>
                    <SelectItem value="CERRADA">Cerrada</SelectItem>
                    </SelectGroup>
                </SelectContent>
            </Select>
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
                    <TableRow
                        key={row.id}
                        data-state={row.getIsSelected() && "selected"}
                    >
                        {/* Filas Tabla */}
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

            {/* Resumen de Arqueo */}
            {/* Se resta el total de todos los saldo_inicial a saldo_final_declarado de cajas cerradas, y se compara con saldo_final_calculado */}
            <div className="text-center sm:text-right text-xl font-bold p-4">
            {(() => {
                const rows = table.getFilteredRowModel().rows as Row<ArqueoCaja>[];

                const cerradas = rows.filter((row) => row.original.estado === "CERRADA");

                const totalGanancia = cerradas.reduce((acc, row) => {
                const { saldo_final_declarado, saldo_inicial } = row.original;
                return acc + ((saldo_final_declarado ?? 0) - (saldo_inicial ?? 0));
                }, 0);

                const totalCalculado = cerradas.reduce((acc, row) => {
                const { saldo_final_calculado } = row.original;
                return acc + (saldo_final_calculado ?? 0);
                }, 0);

                const coincide = totalGanancia === totalCalculado;

                const format = (n: number) =>
                new Intl.NumberFormat("es-AR", {
                    style: "currency",
                    currency: "ARS",
                }).format(n);

                return (
                <div className="flex flex-col md:flex-row gap-6 bg-green-300 px-6 py-4 rounded-lg w-full md:justify-between">
                    <span>Total declarado: {format(totalGanancia)}</span>
                    <span>Total calculado: {format(totalCalculado)}</span>
                    {coincide ? (
                    <span className="text-green-600">✔ Coinciden</span>
                    ) : (
                    <span className="text-red-600">✘ No coinciden</span>
                    )}
                </div>
                );
            })()}
            </div>

        </div>

    </div>
  )
}
