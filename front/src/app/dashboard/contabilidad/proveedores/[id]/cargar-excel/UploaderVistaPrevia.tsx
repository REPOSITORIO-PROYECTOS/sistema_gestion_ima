"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ArrowRight, Check, Loader2, UploadCloud, X } from "lucide-react";

// --- Definición de Tipos de Datos ---

// Define la forma de un artículo en la respuesta de la API de previsualización
interface ArticuloPreview {
  id_articulo: number;
  codigo_interno: string;
  descripcion: string;
  costo_actual: number;
  costo_nuevo: number;
  precio_venta_actual: number;
  precio_venta_nuevo: number;
}

// Define la forma de la respuesta completa de la API
interface PreviewData {
  articulos_a_actualizar: ArticuloPreview[];
  articulos_no_encontrados: string[];
  resumen: string;
}

// --- El punto CLAVE de la conexión ---
// Definimos las props que este componente DEBE recibir del padre
interface UploaderProps {
  proveedorId: number;
  token: string | null;
  API_URL: string;
}

export function UploaderConVistaPrevia({ proveedorId, token, API_URL }: UploaderProps) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePreview = async () => {
    if (!archivo || !token) {
      toast.error("Por favor, selecciona un archivo Excel para continuar.");
      return;
    }
    
    setIsLoading(true);
    setError(null);
    setPreviewData(null);

    const formData = new FormData();
    formData.append('archivo', archivo);

    try {
      const response = await fetch(`${API_URL}/api/importaciones/preview/${proveedorId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Error al procesar el archivo.');

      setPreviewData(data);
      toast.success("Vista previa generada", { description: data.resumen });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Ocurrió un error desconocido.";
      setError(errorMessage);
      toast.error("Error al generar vista previa", { description: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmar = async () => {
    if (!previewData || !token) return;

    setIsLoading(true);
    try {
      const body = JSON.stringify({
        articulos_a_actualizar: previewData.articulos_a_actualizar,
      });

      const response = await fetch(`${API_URL}/api/importaciones/confirmar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: body,
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Error al confirmar los cambios.');
      
      toast.success("Actualización completada", { description: data.message });
      // Limpiamos todo para una nueva subida
      setPreviewData(null);
      setArchivo(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Ocurrió un error desconocido.";
      setError(errorMessage);
      toast.error("Error al confirmar", { description: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-4 border rounded-lg space-y-6 bg-background">
      {/* Sección de Carga de Archivo */}
      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">
          Sube el archivo Excel aquí. El sistema lo analizará y te mostrará los cambios propuestos.
        </p>
        <div className="flex gap-2 items-center">
          <Input 
            type="file" 
            accept=".xlsx, .xls"
            onChange={(e) => setArchivo(e.target.files?.[0] || null)}
            className="flex-grow"
          />
          <Button onClick={handlePreview} disabled={!archivo || isLoading}>
            {isLoading ? <Loader2 className="animate-spin h-4 w-4" /> : <UploadCloud className="h-4 w-4 mr-2" />}
            Previsualizar
          </Button>
        </div>
        {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
      </div>

      {/* Sección de Vista Previa */}
      {previewData && (
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Resultados de la Previsualización</h3>
          <p className="text-sm text-muted-foreground p-3 bg-secondary rounded-md">{previewData.resumen}</p>
          
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Descripción</TableHead>
                  <TableHead className="text-right">Costo Actual</TableHead>
                  <TableHead className="text-right text-blue-500">Costo Nuevo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {previewData.articulos_a_actualizar.map((item) => (
                  <TableRow key={item.id_articulo}>
                    <TableCell>{item.descripcion}</TableCell>
                    <TableCell className="text-right">${item.costo_actual.toFixed(2)}</TableCell>
                    <TableCell className="text-right font-bold text-blue-500 flex items-center justify-end gap-2">
                      <ArrowRight className="h-4 w-4 text-muted-foreground" /> ${item.costo_nuevo.toFixed(2)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {previewData.articulos_no_encontrados.length > 0 && (
            <div>
              <h4 className="font-semibold">Códigos no encontrados</h4>
              <p className="text-xs text-muted-foreground bg-amber-50 p-2 rounded-md border border-amber-200">
                {previewData.articulos_no_encontrados.join(', ')}
              </p>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => setPreviewData(null)} disabled={isLoading}>
              <X className="h-4 w-4 mr-2" /> Cancelar
            </Button>
            <Button onClick={handleConfirmar} disabled={isLoading || previewData.articulos_a_actualizar.length === 0}>
              {isLoading ? <Loader2 className="animate-spin h-4 w-4" /> : <Check className="h-4 w-4 mr-2" />}
              Confirmar y Aplicar Cambios
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}