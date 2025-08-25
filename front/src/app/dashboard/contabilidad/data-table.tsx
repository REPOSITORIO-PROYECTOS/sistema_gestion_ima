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
import { Input } from "@/components/ui/input"
import { Loader2 } from "lucide-react";

import { ModalConfirmacionAccion } from "./ModalConfirmacionAccion";
import { ResumenItemsModal, ItemParaResumen } from "./ResumenItemsModal";
import { useProductoStore } from "@/lib/productoStore";

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

    const [accionActual, setAccionActual] = useState<'agrupar' | 'facturar' | 'anular' | null>(null);
    const [itemsResumen, setItemsResumen] = useState<ItemParaResumen[]>([]);
    const [totalResumen, setTotalResumen] = useState(0);
    const [tipoComprobanteAgrupado, setTipoComprobanteAgrupado] = useState("recibo");
    const productos = useProductoStore((state) => state.productos);

    // --- LÓGICA DE VALIDACIÓN Y PREPARACIÓN (ON-CLICK) ---

    const prepararYAbrirModal = (accion: 'agrupar' | 'facturar') => {
        const selectedRows = table.getSelectedRowModel().flatRows;
        
        // 1. Validación: Selección Mínima
        if (selectedRows.length === 0) {
            toast.info("Por favor, seleccione uno o más movimientos para continuar.");
            return;
        }

        // 2. Validación: Consistencia de la Selección
        const primerItem = selectedRows[0].original;
        const idClienteBase = primerItem.venta?.cliente?.id;
        
        for (const row of selectedRows) {
            if (row.original.venta?.cliente?.id !== idClienteBase) {
                toast.error("Selección inválida", { description: "Todos los movimientos deben pertenecer al mismo cliente." });
                return;
            }
            if (row.original.venta?.facturada) {
                toast.error("Selección inválida", { description: "No se pueden incluir movimientos que ya han sido facturados." });
                return;
            }
            const tipoActual = row.original.venta?.tipo_comprobante_solicitado?.toLowerCase();
            if (accion === 'agrupar' && (tipoActual !== 'presupuesto' && tipoActual !== 'remito')) {
                toast.error("Selección inválida para agrupar", { description: "Solo se pueden agrupar 'Presupuestos' o 'Remitos'." });
                return;
            }
            if (accion === 'facturar' && tipoActual !== 'recibo') {
                toast.error("Selección inválida para facturar", { description: "Solo se pueden facturar 'Recibos'." });
                return;
            }
        }
        
        // 3. Si todas las validaciones pasan, proceder a preparar los datos
        const itemsConsolidados: ItemParaResumen[] = [];
        let totalFinal = 0;
        selectedRows.forEach(row => {
            row.original.venta?.articulos_vendidos?.forEach(itemVendido => {
                const productoActual = productos.find(p => String(p.id) === String(itemVendido.id_articulo));
                const precioUnitarioActualizado = productoActual?.precio_venta ?? itemVendido.precio_unitario;
                const subtotalActualizado = itemVendido.cantidad * precioUnitarioActualizado;
                itemsConsolidados.push({
                    descripcion: itemVendido.nombre,
                    cantidad: itemVendido.cantidad,
                    precio_unitario_antiguo: itemVendido.precio_unitario,
                    precio_unitario_nuevo: precioUnitarioActualizado,
                    subtotal_nuevo: subtotalActualizado,
                });
                totalFinal += subtotalActualizado;
            });
        });
        
        setItemsResumen(itemsConsolidados);
        setTotalResumen(totalFinal);
        setAccionActual(accion);
    };
    
    const handleAnularClick = () => {
        const selectedRows = table.getSelectedRowModel().flatRows;
        
        if (selectedRows.length !== 1) {
            toast.error("Selección inválida", { description: "Para anular, debe seleccionar una única factura." });
            return;
        }

        const rowToAnul = selectedRows[0].original;
        
        if (!rowToAnul.venta || !rowToAnul.venta.facturada) {
            toast.error("Acción no permitida", { description: "Solo se pueden anular movimientos que ya han sido facturados fiscalmente." });
            return;
        }
        
        setAccionActual('anular');
    };
    
    const handleConfirmarAccion = async () => {
        if (!accionActual) return;
        
        setIsLoading(true);
        const selectedRows = table.getSelectedRowModel().flatRows;
        
        let url = '';
        let successMessage = "";

        interface ItemPayload { id_articulo: number; cantidad: number; precio_unitario: number; subtotal: number; nombre: string; }
        interface BodyType { ids_comprobantes?: number[]; ids_movimientos?: number[]; id_movimiento_a_anular?: number; id_cliente_final?: number | null; items?: ItemPayload[]; total_final?: number; nuevo_tipo_comprobante?: string; }
        let body: BodyType = {};

        if (accionActual === 'agrupar' || accionActual === 'facturar') {
            const ids_para_procesar = selectedRows.map(row => row.original.id);
            const id_cliente_final = selectedRows[0]?.original.venta?.cliente?.id ?? null;
            const payloadItems: ItemPayload[] = itemsResumen.map(item => ({
                id_articulo: Number(productos.find(p => p.nombre === item.descripcion)?.id) || 0,
                cantidad: item.cantidad,
                precio_unitario: item.precio_unitario_nuevo,
                subtotal: item.subtotal_nuevo,
                nombre: item.descripcion
            }));
            
            if (accionActual === 'agrupar') {
                url = 'https://sistema-ima.sistemataup.online/api/comprobantes/agrupar';
                body = { ids_comprobantes: ids_para_procesar, id_cliente_final, items: payloadItems, total_final: totalResumen, nuevo_tipo_comprobante: tipoComprobanteAgrupado };
                successMessage = `Se creó el nuevo Comprobante a partir de ${ids_para_procesar.length} movimientos.`;
            } else {
                url = "https://sistema-ima.sistemataup.online/api/comprobantes/facturar-lote";
                body = { ids_movimientos: ids_para_procesar, id_cliente_final, items: payloadItems, total_final: totalResumen };
                successMessage = `Se facturaron con éxito ${ids_para_procesar.length} movimientos.`;
            }
        } else if (accionActual === 'anular') {
            url = 'https://sistema-ima.sistemataup.online/api/comprobantes/anular-factura';
            body = { id_movimiento: selectedRows[0].original.id, };
            successMessage = "La factura ha sido anulada con éxito.";
        }

        try {
            if (!url) throw new Error("Acción no reconocida.");
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify(body)
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Error en la operación: ${accionActual}`);
            }
            toast.success("¡Operación Exitosa!", { description: successMessage });
            table.resetRowSelection();
            onActionComplete();
        } catch (error) {
            if (error instanceof Error) toast.error(`Error al ${accionActual}`, { description: error.message });
        } finally {
            setIsLoading(false);
            setAccionActual(null);
        }
    };

    // --- CONFIGURACIÓN DE LA TABLA (SIMPLIFICADA) ---
    const table = useReactTable<TData>({
        data,
        columns,
        state: { sorting, columnFilters, rowSelection },
        // 'enableRowSelection' se elimina para que todas las casillas estén siempre habilitadas.
        onSortingChange: setSorting,
        onColumnFiltersChange: setColumnFilters,
        onRowSelectionChange: setRowSelection,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
    });

    return (
        <div>
            {/* Contenedor de controles */}
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4">
                
                {/* Grupo de Filtros */}
                <div className="flex flex-col sm:flex-row gap-2 w-full md:flex-grow">
                    <Input
                        placeholder="Buscar por cliente..."
                        value={(table.getColumn("id_cliente")?.getFilterValue() as string) ?? ""}
                        onChange={(event) => table.getColumn("id_cliente")?.setFilterValue(event.target.value)}
                        className="w-full sm:max-w-xs"
                    />
                    <Select
                        value={(table.getColumn("tipo")?.getFilterValue() as string) ?? "all"}
                        onValueChange={(value) => table.getColumn("tipo")?.setFilterValue(value === "all" ? undefined : value)}
                    >
                        <SelectTrigger className="w-full sm:w-[180px]"><SelectValue placeholder="Tipo Movimiento" /></SelectTrigger>
                        <SelectContent><SelectGroup><SelectLabel>Tipo</SelectLabel><SelectItem value="all">Todos</SelectItem><SelectItem value="VENTA">Venta</SelectItem><SelectItem value="APERTURA">Apertura</SelectItem><SelectItem value="CIERRE">Cierre</SelectItem><SelectItem value="EGRESO">Egreso</SelectItem></SelectGroup></SelectContent>
                    </Select>
                    <Select
                        value={facturadoFilter}
                        onValueChange={(value) => { setFacturadoFilter(value); table.getColumn("facturado")?.setFilterValue(value === "all" ? undefined : value); }}
                    >
                        <SelectTrigger className="w-full sm:w-[180px]"><SelectValue placeholder="Facturación" /></SelectTrigger>
                        <SelectContent><SelectGroup><SelectLabel>Facturación</SelectLabel><SelectItem value="all">Todos</SelectItem><SelectItem value="true">Facturados</SelectItem><SelectItem value="false">No Facturados</SelectItem></SelectGroup></SelectContent>
                    </Select>
                </div>
        
                {/* Grupo de Botones de Acción - Siempre Visibles */}
                <div className="flex w-full md:w-auto md:flex-shrink-0 gap-2">
                    <Button 
                        className="flex-1 md:flex-initial" 
                        variant="outline" 
                        onClick={() => prepararYAbrirModal('facturar')}
                        disabled={isLoading}
                    >
                        {isLoading ? <Loader2 className="animate-spin h-4 w-4" /> : `Facturar Lote`}
                    </Button>
                    <Button 
                        className="flex-1 md:flex-initial" 
                        variant="outline"
                        onClick={() => prepararYAbrirModal('agrupar')}
                        disabled={isLoading}
                    >
                         {isLoading ? <Loader2 className="animate-spin h-4 w-4" /> : `Agrupar`}
                    </Button>
                    <Button 
                        className="flex-1 md:flex-initial" 
                        variant="destructive"
                        onClick={handleAnularClick}
                        disabled={isLoading}
                    >
                        {isLoading ? <Loader2 className="animate-spin h-4 w-4" /> : `Anular`}
                    </Button>
                </div>
            </div>

            {/* Tabla Principal */}
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

            {/* Paginación y Footer */}
            <div className="flex items-center justify-between space-x-2 py-4">
                <div className="flex-1 text-sm text-muted-foreground">
                    {table.getFilteredSelectedRowModel().rows.length} de {table.getFilteredRowModel().rows.length} fila(s) seleccionadas.
                </div>
                <div>
                    <Button variant="outline" size="sm" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>Anterior</Button>
                    <Button variant="outline" size="sm" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>Siguiente</Button>
                </div>
            </div>

            {/* Modal Reutilizable */}
            <ModalConfirmacionAccion
                isOpen={accionActual !== null}
                onClose={() => setAccionActual(null)}
                onConfirm={handleConfirmarAccion}
                isLoading={isLoading}
                titulo={
                    accionActual === 'agrupar' ? "Agrupar a Comprobante" :
                    accionActual === 'facturar' ? "Facturar Lote" : "Anular Factura"
                }
                descripcion={
                    accionActual === 'anular' 
                    ? `Estás a punto de emitir una Nota de Crédito para anular la factura seleccionada. Esta acción es irreversible. ¿Deseas continuar?`
                    : `Revisa los detalles antes de confirmar. Los precios han sido actualizados a la fecha.`
                }
                textoBotonConfirmar={
                    accionActual === 'anular' ? "Sí, Anular Factura" : "Confirmar"
                }
                mostrarSelector={accionActual === 'agrupar'}
                valorSelector={tipoComprobanteAgrupado}
                onSelectorChange={setTipoComprobanteAgrupado}
                opcionesSelector={[
                    { value: 'recibo', label: 'Recibo (No Fiscal)' },
                    { value: 'factura', label: 'Factura (Fiscal)' }
                ]}
            >
                {accionActual !== 'anular' && (
                    <ResumenItemsModal items={itemsResumen} totalFinal={totalResumen} />
                )}
            </ModalConfirmacionAccion>
        </div>
    );
}