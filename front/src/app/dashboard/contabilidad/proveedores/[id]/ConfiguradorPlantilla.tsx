"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Save } from "lucide-react";

// --- Tipos de Datos ---
// La "forma" de los datos de una plantilla existente
interface PlantillaExistente {
  nombre_plantilla: string;
  mapeo_columnas: { [key: string]: string };
  nombre_hoja_excel?: string | null;
  fila_inicio: number;
}
// Las props que este componente necesita recibir de su padre
interface ConfiguradorPlantillaProps {
  proveedorId: number;
  token: string | null;
  plantillaActual?: PlantillaExistente | null; // La plantilla puede existir o no
  onPlantillaGuardada: () => void; // Función para notificar al padre que se guardó
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://sistema-ima.sistemataup.online";

export function ConfiguradorPlantilla({ proveedorId, token, plantillaActual, onPlantillaGuardada }: ConfiguradorPlantillaProps) {
  // --- Estados del Formulario ---
  // Inicializamos los estados con los datos de la plantilla actual, si existe.
  // Si no, usamos valores por defecto.
  const [nombrePlantilla, setNombrePlantilla] = useState(plantillaActual?.nombre_plantilla || "Plantilla Principal");
  const [nombreHoja, setNombreHoja] = useState(plantillaActual?.nombre_hoja_excel || "");
  const [filaInicio, setFilaInicio] = useState(plantillaActual?.fila_inicio || 2);
  
  // Extraemos los valores específicos del mapeo que nos interesan
  const [colCodigo, setColCodigo] = useState(plantillaActual?.mapeo_columnas?.codigo_articulo_proveedor || "");
  const [colCosto, setColCosto] = useState(plantillaActual?.mapeo_columnas?.precio_costo || "");

  const [isLoading, setIsLoading] = useState(false);

  // --- Lógica de Envío del Formulario ---
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    // Validación simple para los campos más importantes
    if (!nombrePlantilla || !colCodigo || !colCosto) {
      toast.error("Por favor, completa los campos obligatorios: Nombre de Plantilla, Columna de Código y Columna de Costo.");
      return;
    }
    setIsLoading(true);
    
    // Construimos el objeto de datos (payload) que enviaremos a la API,
    // asegurándonos de que coincida con el schema del backend.
    const payload = {
      id_proveedor: proveedorId,
      nombre_plantilla: nombrePlantilla,
      mapeo_columnas: {
        codigo_articulo_proveedor: colCodigo,
        precio_costo: colCosto,
      },
      nombre_hoja_excel: nombreHoja || null, // Si está vacío, se envía null
      fila_inicio: Number(filaInicio),
    };

    try {
      const response = await fetch(`${API_URL}/api/proveedores/plantilla`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Error al guardar la plantilla.");

      toast.success("Plantilla guardada correctamente");
      onPlantillaGuardada(); // Avisamos al componente padre para que refresque los datos
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Ocurrió un error desconocido.";
      toast.error("Error al guardar", { description: errorMessage });
    } finally {
      setIsLoading(false);
    }
  };

  // --- Renderizado del Componente ---
  return (
    <Card>
      <CardHeader>
        <CardTitle>Configuración de Plantilla de Importación</CardTitle>
        <CardDescription>
          {plantillaActual ? "Edita la configuración" : "Crea una nueva configuración"} para que el sistema pueda leer los archivos Excel de este proveedor.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          
          {/* Campos Generales de la Plantilla */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="nombrePlantilla">Nombre de la Plantilla</Label>
              <Input id="nombrePlantilla" value={nombrePlantilla} onChange={(e) => setNombrePlantilla(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="nombreHoja">Nombre de la Hoja Excel (Opcional)</Label>
              <Input id="nombreHoja" value={nombreHoja} onChange={(e) => setNombreHoja(e.target.value)} placeholder="Ej: 'Lista Precios' o dejar vacío" />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="filaInicio">Los datos comienzan en la fila número</Label>
            <Input id="filaInicio" type="number" min="1" value={filaInicio} onChange={(e) => setFilaInicio(Number(e.target.value))} required />
          </div>

          {/* Sub-tarjeta para el Mapeo de Columnas */}
          <Card className="bg-secondary/50 pt-4">
            <CardHeader className="py-0 px-6">
              <CardTitle className="text-base">Mapeo de Columnas Obligatorias</CardTitle>
              <CardDescription className="text-xs">
                Escribe el nombre EXACTO de la columna como aparece en tu archivo Excel.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label htmlFor="colCodigo">Columna para el <span className="font-mono text-primary bg-background px-1 rounded">Código del Artículo</span></Label>
                <Input id="colCodigo" value={colCodigo} onChange={(e) => setColCodigo(e.target.value)} placeholder="Ej: SKU, Codigo, Referencia" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="colCosto">Columna para el <span className="font-mono text-primary bg-background px-1 rounded">Precio de Costo</span></Label>
                <Input id="colCosto" value={colCosto} onChange={(e) => setColCosto(e.target.value)} placeholder="Ej: Precio Neto, Costo Unitario" required />
              </div>
            </CardContent>
          </Card>
          
          {/* Botón de Envío */}
          <div className="flex justify-end pt-2">
            <Button type="submit" disabled={isLoading} size="lg">
              {isLoading ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : <Save className="h-4 w-4 mr-2" />}
              {plantillaActual ? "Actualizar Plantilla" : "Guardar Plantilla"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}