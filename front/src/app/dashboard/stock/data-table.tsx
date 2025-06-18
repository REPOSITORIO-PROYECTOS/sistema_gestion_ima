"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

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

import AddStockForm from "./StockForm"


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
    const [currentStatus, setCurrentStatus] = useState("all")

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

        {/* Selectores Filtrado */}
        <div className="flex items-center pb-4 justify-between">


            {/* Input de Búsqueda por email */}
            <Input placeholder="Filtrar por producto" value={(table.getColumn("producto")?.getFilterValue() as string) ?? ""}
            onChange={(event) => table.getColumn("producto")?.setFilterValue(event.target.value)} className="max-w-48" />


            <div className="flex flex-row-reverse items-center gap-2">

                {/* Modal para crear items */}
                <Dialog>
                    <DialogTrigger asChild>
                        <Button variant="outline">Agregar Producto +</Button>
                    </DialogTrigger>

                    <DialogContent className="sm:max-w-lg">
                        <DialogHeader>
                        <DialogTitle>Agregar un Producto Nuevo</DialogTitle>
                        <DialogDescription>Todos los campos son obligatorios</DialogDescription>
                        </DialogHeader>

                        {/* Llamamos al Form con el modo crear */}
                        <AddStockForm mode="create" />
                    </DialogContent>
                </Dialog>

            

                {/* Input de Seleccion por status */}
                <Select value={currentStatus} onValueChange={(value) => {
                setCurrentStatus(value)
                table.getColumn("ubicacion")?.setFilterValue(value === "all" ? undefined : value)}}>

                    <SelectTrigger className="w-[180px] cursor-pointer">
                        <SelectValue placeholder="Ubicación"/>
                    </SelectTrigger>

                    <SelectContent>
                        <SelectGroup>
                            <SelectLabel>Ubicación</SelectLabel>
                            <SelectItem value="all">Todos</SelectItem>
                            <SelectItem value="Depósito A">Depósito A</SelectItem>
                            <SelectItem value="Depósito B">Depósito B</SelectItem>
                            <SelectItem value="Sucursal Centro">Sucursal Centro</SelectItem>
                            <SelectItem value="Sucursal Norte">Sucursal Norte</SelectItem>
                        </SelectGroup>
                    </SelectContent>

                </Select>

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
            <div className="flex flex-row-reverse justify-between items-center mx-2 ">

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
            </div>

        </div>

    </div>
  )
}
