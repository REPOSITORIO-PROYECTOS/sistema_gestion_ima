"use client";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

// Definimos la forma de un solo objeto de mapeo
type MapeoPlantilla = {
  columna_excel: string;
  campo_db: string;
};

// --- El punto CLAVE de la conexión ---
// Definimos que este componente DEBE recibir una prop llamada 'plantilla',
// y que esa prop debe ser un array de objetos 'MapeoPlantilla'.
interface PlantillaGuiaProps {
  plantilla: MapeoPlantilla[];
}

// Usamos '{ plantilla }' para "desempacar" la prop que nos pasó el padre.
export function PlantillaGuia({ plantilla }: PlantillaGuiaProps) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nombre de Columna en tu Excel</TableHead>
            <TableHead>Campo que Actualizará</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {plantilla.length > 0 ? (
            plantilla.map((mapeo, index) => (
              <TableRow key={index}>
                <TableCell className="font-mono font-semibold">{mapeo.columna_excel}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{mapeo.campo_db}</Badge>
                </TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={2} className="text-center text-muted-foreground">
                No hay una plantilla de importación configurada para este proveedor.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}