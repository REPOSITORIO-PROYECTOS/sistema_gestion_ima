"use client";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
// No necesitamos importar Alert ni ScrollArea

// La interfaz de la respuesta del backend
export interface PrevisualizacionResponse {
    resumen: string;
    articulos_no_encontrados: string[];
    articulos_a_actualizar: {
        id_articulo: number;
        codigo_interno: string;
        descripcion: string;
        costo_actual: number;
        costo_nuevo: number;
        precio_venta_actual: number;
        precio_venta_nuevo: number;
    }[];
}

interface Props {
    data: PrevisualizacionResponse;
    isLoading: boolean;
    onConfirm: () => void;
    onCancel: () => void;
}

export const PreviewChanges: React.FC<Props> = ({ data, isLoading, onConfirm, onCancel }) => {
    
    const hayCambios = data.articulos_a_actualizar.length > 0;

    return (
        <div>
            {/* --- REEMPLAZO DE <Alert> --- */}
            {/* Un div con clases de Tailwind para simular una alerta */}
            <div className="mb-4 rounded-lg border bg-card text-card-foreground shadow-sm p-4">
                <h3 className="mb-1 font-medium leading-none tracking-tight">Resumen de la Previsualización</h3>
                <div className="text-sm text-muted-foreground">
                    {data.resumen}
                </div>
            </div>

            <h3 className="text-lg font-semibold mb-2">Artículos a Actualizar</h3>
            {/* --- REEMPLAZO DE <ScrollArea> --- */}
            {/* Un div con una altura fija y overflow para hacer scroll */}
            <div className="w-full rounded-md border h-72 overflow-y-auto">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Artículo</TableHead>
                            <TableHead className="text-right">Costo Actual</TableHead>
                            <TableHead className="text-right font-bold text-blue-600">Costo Nuevo</TableHead>
                            <TableHead className="text-right">Venta Actual</TableHead>
                            <TableHead className="text-right font-bold text-green-600">Venta Nuevo</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {hayCambios ? (
                            data.articulos_a_actualizar.map((item) => (
                                <TableRow key={item.id_articulo}>
                                    <TableCell>
                                        <p className="font-medium">{item.descripcion}</p>
                                        <p className="text-xs text-muted-foreground">{item.codigo_interno}</p>
                                    </TableCell>
                                    <TableCell className="text-right">${item.costo_actual.toFixed(2)}</TableCell>
                                    <TableCell className="text-right font-semibold text-blue-600">${item.costo_nuevo.toFixed(2)}</TableCell>
                                    <TableCell className="text-right">${item.precio_venta_actual.toFixed(2)}</TableCell>
                                    <TableCell className="text-right font-semibold text-green-600">${item.precio_venta_nuevo.toFixed(2)}</TableCell>
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                                    No se encontraron cambios de precio para aplicar.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>
            
            {/* Alerta de códigos no encontrados (si los hay) */}
            {data.articulos_no_encontrados.length > 0 && (
                <div className="mt-4 rounded-lg border bg-destructive/10 text-destructive p-4">
                    <h3 className="mb-1 font-medium leading-none tracking-tight">Códigos de Proveedor no Encontrados</h3>
                    <div className="text-sm">
                        {data.articulos_no_encontrados.join(", ")}
                    </div>
                </div>
            )}
            
            {/* Botones de Acción */}
            <div className="flex justify-end gap-2 mt-6">
                <Button variant="ghost" onClick={onCancel} disabled={isLoading}>
                    Cancelar y Cargar Otro Archivo
                </Button>
                <Button 
                    onClick={onConfirm} 
                    disabled={isLoading || !hayCambios}
                >
                    {isLoading ? "Confirmando..." : `Confirmar y Aplicar ${data.articulos_a_actualizar.length} Cambios`}
                </Button>
            </div>
        </div>
    );
};