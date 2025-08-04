"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
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
            const tipoSolicitado = row.original.venta?.tipo_comprobante_solicitado;

            // No permitir selección de EGRESO o facturada
            if (tipo === "EGRESO" || facturada === true) return false;

            const selectedKeys = Object.keys(rowSelection);
            if (selectedKeys.length === 0) return true;

            // Obtener la primera fila seleccionada
            const primeraSeleccionada = data.find((item) =>
                selectedKeys.includes(String(item.id))
            );
            if (!primeraSeleccionada) return true;

            const tipoSolicitadoBase = primeraSeleccionada.venta?.tipo_comprobante_solicitado;

            // Si no hay tipo solicitado base, permitimos libre selección
            if (!tipoSolicitadoBase) return true;

            // Solo permitir si coincide el tipo_comprobante_solicitado
            return tipoSolicitado === tipoSolicitadoBase;
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

                    {/* Selectores y Filtrados */}
                    <div className="flex flex-col md:flex-row w-full md:w-auto gap-4">

                        {/* Elegir por tipo de movimiento */}
                        <Select
                            value={(table.getColumn("tipo")?.getFilterValue() as string) ?? "all"}
                            onValueChange={(value) => {
                                table.getColumn("tipo")?.setFilterValue(value === "all" ? undefined : value);
                            }}
                            >
                            <SelectTrigger className="w-full md:w-[180px] cursor-pointer">
                                <SelectValue placeholder="Tipo de Movimiento" />
                            </SelectTrigger>

                            <SelectContent>
                                <SelectGroup>
                                <SelectLabel>Tipo de Movimiento</SelectLabel>
                                <SelectItem value="all">Movimientos</SelectItem>
                                <SelectItem value="APERTURA">APERTURA</SelectItem>
                                <SelectItem value="CIERRE">CIERRE</SelectItem>
                                <SelectItem value="VENTA">VENTA</SelectItem>
                                <SelectItem value="EGRESO">EGRESO</SelectItem>
                                </SelectGroup>
                            </SelectContent>
                        </Select>

                        {/* Si esta facturado o no el movimiento.. */}
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
                                    <SelectLabel>Movimientos Facturados</SelectLabel>
                                    <SelectItem value="all">Facturados S/N</SelectItem>
                                    <SelectItem value="true">Facturados</SelectItem>
                                    <SelectItem value="false">No Facturados</SelectItem>
                                </SelectGroup>
                            </SelectContent>
                        </Select>
                    </div>
            
                    {/* --- Botones de Facturación --- */}
                    <div className="flex flex-col md:flex-row w-1/2 gap-4 px-4">
                        <Button
                            className="w-1/2"
                            variant="outline"
                            onClick={() => console.log("Lógica para facturar lote")}
                            disabled={!table.getIsSomeRowsSelected() || isLoading}
                        >
                            Facturar Lote ({table.getFilteredSelectedRowModel().rows.length})
                        </Button>
                        <Button
                            className="w-1/2"
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