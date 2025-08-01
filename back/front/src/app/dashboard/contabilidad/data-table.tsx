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
import { MovimientoAPI } from "./columns";

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
}

export function DataTable<TData extends MovimientoAPI, TValue>({
  columns,
  data,
}: DataTableProps<TData, TValue>) {
    
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
    const [facturadoFilter, setFacturadoFilter] = useState("all");
    const [rowSelection, setRowSelection] = useState({});

    const table = useReactTable<TData>({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        enableRowSelection: (row) => {
        const tipo = row.original.tipo;
        const facturada = row.original.venta?.facturada;
        const tipoComprobante = row.original.tipo_comprobante;

        // No permitir selección si es EGRESO o ya facturada
        if (tipo === "EGRESO" || facturada === true) return false;

        // Si no hay ninguna fila seleccionada, permitir cualquiera
        const selectedKeys = Object.keys(rowSelection);
        if (selectedKeys.length === 0) return true;

        // Buscar la primera fila seleccionada
        const selectedRow = data.find((item) =>
            selectedKeys.includes(item.id.toString())
        );

        if (!selectedRow) return true;

        // Permitir solo si el tipo_comprobante es igual
        return tipoComprobante === selectedRow.tipo_comprobante;
        },
        onSortingChange: setSorting,
        onColumnFiltersChange: setColumnFilters,
        onRowSelectionChange: setRowSelection,
        state: {
        sorting,
        columnFilters,
        rowSelection,
        },
    });

    return (

        <div>

            {/* Inputs de Filtrado + Creación */}
            <div className="flex flex-col md:flex-row-reverse justify-between gap-2 pb-4">

                {/* Inputs de Filtrado */}
                <div className="flex flex-col-reverse md:flex-row justify-between items-center gap-2 w-full">

                    <div className="flex flex-col md:flex-row w-full md:w-2/3 gap-4">
                        {/* Input de Búsqueda por Producto */}
                        <Input
                            placeholder="Filtrar por tipo"
                            value={(table.getColumn("tipo")?.getFilterValue() as string) ?? ""}
                            onChange={(event) =>
                                table.getColumn("tipo")?.setFilterValue(event.target.value)
                            }
                            className="w-full md:w-1/4"
                        />

                        {/* Dropdown de si esta facturado o no */}
                        <Select
                            value={facturadoFilter}
                            onValueChange={(value) => {
                                setFacturadoFilter(value);
                                table.getColumn("facturado")?.setFilterValue(
                                    value === "all" ? undefined : value
                                );
                            }}
                            >
                            <SelectTrigger className="w-full md:w-1/4 cursor-pointer">
                                <SelectValue placeholder="Facturado" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectGroup>
                                <SelectLabel>Facturado</SelectLabel>
                                <SelectItem value="all">Todos</SelectItem>
                                <SelectItem value="true">Sí</SelectItem>
                                <SelectItem value="false">No</SelectItem>
                                </SelectGroup>
                            </SelectContent>
                        </Select>
                    </div>
            
                    {/* Facturador Global */}
                    <Button
                        className="w-full md:w-1/4"
                        variant="outline"
                        onClick={() => {
                            const selected = table.getSelectedRowModel().rows.map(row => row.original);
                            console.log("Filas seleccionadas:", selected);
                            // acá podrías hacer un fetch o lo que necesites
                        }}
                    >
                        Facturar Lote
                    </Button>
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
                            <TableHead className="px-4" key={header.id}>
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