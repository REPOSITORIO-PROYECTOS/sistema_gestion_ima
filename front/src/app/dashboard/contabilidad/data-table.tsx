"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  flexRender,
  Row,
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
import { Input } from "@/components/ui/input"

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

    // Agrupar Movimientos
    const handleAgrupar = async () => {
        setIsLoading(true);
        const selectedRows: Row<TData>[] = table.getSelectedRowModel().flatRows; 
        const idsParaAgrupar = selectedRows.map(row => row.original.id);
        try {
            if (selectedRows.length === 0) {
                toast.error("Selección inválida", { description: "Debes seleccionar al menos un presupuesto o remito." });
                setIsLoading(false);
                return;
            }

            // --- VALIDACIÓN #1: Asegurarse de que SÓLO sean Presupuestos o Remitos ---
            const esValidoParaAgrupar = selectedRows.every(row => {
                const tipo = row.original.venta?.tipo_comprobante_solicitado?.toLowerCase();
                return tipo === 'presupuesto' || tipo === 'remito';
            });

            if (!esValidoParaAgrupar) {
                toast.error("Error de selección", { description: "Solo puedes agrupar movimientos de tipo 'Presupuesto' o 'Remito'." });
                setIsLoading(false);
                return;
            }
            
            // --- VALIDACIÓN #2: Que todos pertenezcan al mismo cliente ---
            const clientes = selectedRows.map(row => row.original.venta?.cliente?.id ?? null);
            const todosIguales = clientes.every(id => id === clientes[0]);
            if (!todosIguales) {
                toast.error("Error de selección", { description: "Todos los movimientos deben pertenecer al mismo cliente." });
                setIsLoading(false);
                return;
            }
            
            // --- Construcción del Payload ---
            const ids_movimientos = selectedRows.map(row => row.original.id);
            const id_cliente_final = clientes[0] && clientes[0] !== 0 ? clientes[0] : null;

            // --- LLAMADA AL ENDPOINT CORRECTO: Convertir a Venta No Fiscal ---
            const response = await fetch('https://sistema-ima.sistemataup.online/api/comprobantes/agrupar-a-comprobante', { // <-- ENDPOINT ESPECÍFICO
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    ids_movimientos,
                    id_cliente_final
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error en el servidor al agrupar.');
            }

            const nuevoComprobante = await response.json();
            
            // --- MENSAJE DE ÉXITO CORREGIDO ---
            toast.success("¡Agrupación Exitosa!", {
                description: `Se creó el Comprobante Interno ID: ${nuevoComprobante.id_movimiento_nuevo} a partir de ${ids_movimientos.length} movimientos.`
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

    // POST para facturar movimientos (ventas) en el back
    const handleFacturarLote = async () => {
        setIsLoading(true);

        try {
            const selectedRows = table.getSelectedRowModel().flatRows;

            if (selectedRows.length === 0) {
                toast.error("Selección inválida", {
                    description: "Debes seleccionar al menos una venta."
                });
                setIsLoading(false);
                return;
            }

            // Validar que todos los clientes sean iguales
            const clientes = selectedRows.map(row => row.original.venta?.cliente?.id ?? null);
            const todosIguales = clientes.every(id => id === clientes[0]);

            if (!todosIguales) {
                toast.error("Error de selección", {
                    description: "Todas las ventas seleccionadas deben pertenecer al mismo cliente."
                });
                setIsLoading(false);
                return;
            }

            const ids_movimientos = selectedRows.map(row => row.original.id);
            const id_cliente_final = clientes[0] && clientes[0] !== 0 ? clientes[0] : null;

            const response = await fetch(
                "https://sistema-ima.sistemataup.online/api/comprobantes/facturar-lote",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({
                        ids_movimientos,
                        id_cliente_final,
                    }),
                }
            );

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Error en la facturación del lote.");
            }

            toast.success("¡Facturación exitosa!", {
                description: `Se facturaron ${ids_movimientos.length} movimientos correctamente.`
            });

            table.resetRowSelection();
            onActionComplete();

        } catch (error) {
            toast.error("Error al facturar", {
                description: error instanceof Error ? error.message : "Ocurrió un error inesperado."
            });
        } finally {
            setIsLoading(false);
        }
    };

    // Generador de tabla
    const table = useReactTable<TData>({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        enableRowSelection: (row: Row<TData>): boolean => { // <--- AÑADE EL TIPO AQUÍ
            const facturada = row.original.venta?.facturada;
            const tipo = row.original.tipo;

            // Condición base: No se puede seleccionar si ya está facturado o no es una VENTA
            if (facturada === true || tipo !== 'VENTA') {
                return false;
            }

            const selectedRows = table.getSelectedRowModel().flatRows;
            // Si es el primer item a seleccionar, es válido
            if (selectedRows.length === 0) {
                return true;
            }

            // Si ya hay algo seleccionado, aplicamos las reglas de consistencia
            const primerItem = selectedRows[0].original;
            const primerClienteId = primerItem.venta?.cliente?.id ?? null;
            const clienteActualId = row.original.venta?.cliente?.id ?? null;

            // Regla #1: El cliente DEBE ser el mismo
            if (clienteActualId !== primerClienteId) {
                return false;
            }

            // Regla #2: No se pueden mezclar Presupuestos/Remitos con otros comprobantes
            const primerTipo = primerItem.venta?.tipo_comprobante_solicitado?.toLowerCase();
            const esPrimerItemAgrupable = primerTipo === 'presupuesto' || primerTipo === 'remito';

            const tipoActual = row.original.venta?.tipo_comprobante_solicitado?.toLowerCase();
            const esItemActualAgrupable = tipoActual === 'presupuesto' || tipoActual === 'remito';

            return esPrimerItemAgrupable === esItemActualAgrupable;
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
            {/* Opciones de la Tavla */}
            <div className="flex flex-col md:flex-row-reverse justify-between gap-2 pb-4">
                <div className="flex flex-col md:flex-row justify-between items-center gap-4 w-full">

                    {/* Selectores y Filtrados */}
                    <div className="flex flex-col md:flex-row w-full md:w-auto gap-4">

                        {/* Input de busqueda por nombre de cliente para facturarle */}
                        <Input
                            placeholder="Buscar cliente..."
                            value={(table.getColumn("id_cliente")?.getFilterValue() as string) ?? ""}
                            onChange={(event) =>
                                table.getColumn("id_cliente")?.setFilterValue(event.target.value)
                            }
                            className="w-full md:w-1/3"
                        />

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
                    <div className="flex flex-col md:flex-row w-full md:w-1/3 md:px-4 gap-4">
                        <Button
                            className="w-full md:w-1/2"
                            variant="outline"
                            onClick={handleFacturarLote}
                            disabled={!table.getIsSomeRowsSelected() || isLoading}
                        >
                            Facturar Lote ({table.getFilteredSelectedRowModel().rows.length})
                        </Button>
                        <Button
                            className="w-full md:w-1/2"
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

            {/* Tabla */}
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

            {/* Footer Tabla */}
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