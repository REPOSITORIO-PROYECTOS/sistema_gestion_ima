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
import { toast } from "sonner";
// import { on } from "events"; // <-- CORRECCIÓN: Eliminada esta importación que no se usa.

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  token: string | null;
  onActionComplete: () => void;
}

export function DataTable<TData extends MovimientoAPI, TValue>({
  columns,
  data,
  token,
  onActionComplete
}: DataTableProps<TData, TValue>) {
    
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
    const [facturadoFilter, setFacturadoFilter] = useState("all");
    const [rowSelection, setRowSelection] = useState({});
    const [isLoading, setIsLoading] = useState(false);

     const handleAgrupar = async () => {
        setIsLoading(true);

        const selectedRows = table.getSelectedRowModel().flatRows;
        const idsParaAgrupar = selectedRows.map(row => row.original.id);
        
        const yaFacturado = selectedRows.some(row => row.original.venta?.facturada === true);
        if (yaFacturado) {
            toast.error("Error de selección", {
                description: "No puedes agrupar movimientos que ya han sido facturados.",
            });
            setIsLoading(false);
            return;
        }

        try {
            const response = await fetch('/api/comprobantes/agrupar', {
                method: 'POST',
                headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                ids_comprobantes: idsParaAgrupar,
                nuevo_tipo_comprobante: 'Factura A'
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ocurrió un error en el servidor.');
            }

            const nuevoComprobante = await response.json();
            
            toast.success("¡Operación Exitosa!", {
                description: `Se creó la Factura ID: ${nuevoComprobante.id} agrupando ${idsParaAgrupar.length} movimientos.`
            });

            table.resetRowSelection();
            onActionComplete();

        } catch (error) {
            if (error instanceof Error) {
                toast.error("Error al agrupar", {
                    description: error.message
                });
            }
        } finally {
            setIsLoading(false);
        }
    };

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

            if (tipo === "EGRESO" || facturada === true) return false;

            const selectedKeys = Object.keys(rowSelection);
            if (selectedKeys.length === 0) return true;

            const primeraFilaSeleccionada = data.find(item => selectedKeys.includes(String(item.id)));
            if (!primeraFilaSeleccionada) return true;
            
            return tipoComprobante === primeraFilaSeleccionada.tipo_comprobante;
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
            <div className="flex flex-col md:flex-row-reverse justify-between gap-2 pb-4">

                <div className="flex flex-col-reverse md:flex-row justify-between items-center gap-2 w-full">

                    <div className="flex flex-col md:flex-row w-full md:w-auto gap-4">
                        <Input
                            placeholder="Filtrar por tipo"
                            value={(table.getColumn("tipo")?.getFilterValue() as string) ?? ""}
                            onChange={(event) =>
                                table.getColumn("tipo")?.setFilterValue(event.target.value)
                            }
                            className="w-full md:w-auto"
                        />
                        <Select
                            value={facturadoFilter}
                            onValueChange={(value) => {
                                setFacturadoFilter(value);
                                table.getColumn("facturado")?.setFilterValue(
                                    value === "all" ? undefined : value
                                );
                            }}
                            >
                            <SelectTrigger className="w-full md:w-[180px] cursor-pointer">
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
            
                    {/* --- CORRECCIÓN: Botones de acción agrupados --- */}
                    <div className="flex w-full md:w-auto gap-2">
                        <Button
                            className="w-full"
                            variant="outline"
                            onClick={() => console.log("Lógica para facturar lote")}
                            disabled={!table.getIsSomeRowsSelected() || isLoading}
                        >
                            Facturar Lote ({table.getFilteredSelectedRowModel().rows.length})
                        </Button>
                        <Button
                            className="w-full"
                            variant="default"
                            disabled={!table.getIsSomeRowsSelected() || isLoading}
                            onClick={handleAgrupar} 
                            >
                            {isLoading 
                                ? "Procesando..." 
                                : `Agrupar (${table.getFilteredSelectedRowModel().rows.length})`
                            }
                        </Button>
                    </div>

                </div>
            </div>

            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                    {table.getHeaderGroups().map((headerGroup) => (
                        <TableRow key={headerGroup.id}>
                        {headerGroup.headers.map((header) => (
                            <TableHead className="px-4" key={header.id}>
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
                            No hay resultados que coincidan con la búsqueda.
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
    )
}