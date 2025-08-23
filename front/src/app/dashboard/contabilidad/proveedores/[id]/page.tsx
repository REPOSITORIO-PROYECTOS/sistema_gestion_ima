"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Loader2, Upload } from "lucide-react";

// Importamos el componente del formulario de configuración
import { ConfiguradorPlantilla } from "./ConfiguradorPlantilla";

// --- Definición de Tipos de Datos ---
// La "forma" completa de los datos que esperamos de la API para esta página
interface PlantillaMapeo {
  nombre_plantilla: string;
  mapeo_columnas: { [key: string]: string };
  nombre_hoja_excel?: string | null;
  fila_inicio: number;
}

interface ProveedorConPlantilla {
  id: number;
  nombre_razon_social: string;
  nombre_fantasia: string | null;
  cuit: string | null;
  condicion_iva: string;
  email: string | null;
  telefono: string | null;
  // El campo clave: puede ser un objeto de plantilla, null, o no existir
  plantilla_mapeo?: PlantillaMapeo | null;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://sistema-ima.sistemataup.online";

// --- Componente Principal de la Página ---
export default function ProveedorDetailPage() {
  const params = useParams();
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  
  // Normalizamos el ID del proveedor desde la URL
  const proveedorId = Number(Array.isArray(params.id) ? params.id[0] : params.id);
  
  // --- Estados del Componente ---
  const [proveedor, setProveedor] = useState<ProveedorConPlantilla | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // --- Lógica de Carga de Datos ---
  // Usamos useCallback para que la función no se recree en cada render,
  // lo cual es una optimización importante.
  const fetchProveedor = useCallback(async () => {
    if (!token || !proveedorId || isNaN(proveedorId)) {
        setIsLoading(false);
        return;
    };

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/proveedores/${proveedorId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "No se pudo cargar el proveedor.");
      }

      const data = await response.json();
      setProveedor(data);

    } catch (error) {
      if (error instanceof Error) {
        toast.error("Error al cargar proveedor", { description: error.message });
      }
    } finally {
      setIsLoading(false);
    }
  }, [proveedorId, token]);

  // useEffect se ejecuta una vez cuando el componente se monta para cargar los datos
  useEffect(() => {
    fetchProveedor();
  }, [fetchProveedor]);


  // --- Renderizado Condicional ---
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin h-8 w-8 text-primary" />
        <p className="ml-4 text-muted-foreground">Cargando datos del proveedor...</p>
      </div>
    );
  }

  if (!proveedor) {
    return (
      <div className="p-6 text-center">
        <p className="text-red-500 font-semibold">Proveedor no encontrado.</p>
        <p className="text-sm text-muted-foreground mt-2">No se pudieron cargar los datos. Es posible que el proveedor no exista o haya ocurrido un error.</p>
        <Button variant="outline" onClick={() => router.back()} className="mt-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Volver
        </Button>
      </div>
    );
  }

  // --- Renderizado Principal ---
  return (
    <div className="p-4 md:p-6 space-y-8">
      {/* Sección de Encabezado y Datos Básicos */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
            <div className="space-y-1">
                <CardTitle className="text-2xl">{proveedor.nombre_razon_social}</CardTitle>
                <CardDescription>
                    CUIT: {proveedor.cuit || "No especificado"} - IVA: {proveedor.condicion_iva}
                </CardDescription>
            </div>
            <Button variant="outline" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Volver
            </Button>
        </CardHeader>
        <CardContent>
            {/* Aquí puedes agregar más detalles del proveedor si lo deseas */}
            <p><strong>Email:</strong> {proveedor.email || "N/A"}</p>
            <p><strong>Teléfono:</strong> {proveedor.telefono || "N/A"}</p>
        </CardContent>
      </Card>
      
      {/* Sección para Configurar la Plantilla */}
      <ConfiguradorPlantilla 
        proveedorId={proveedor.id}
        token={token}
        plantillaActual={proveedor.plantilla_mapeo}
        onPlantillaGuardada={fetchProveedor}
      />

      {/* Sección de "Siguiente Paso": el botón para ir a cargar el Excel */}
      <Card>
        <CardHeader>
          <CardTitle>Siguiente Paso: Cargar Archivo</CardTitle>
          <CardDescription>
            Una vez que la plantilla esté configurada y guardada, puedes proceder a cargar la lista de precios.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link href={`/dashboard/contabilidad/proveedores/${proveedor.id}/cargar-excel`} passHref>
            <Button size="lg" disabled={!proveedor.plantilla_mapeo}> {/* El botón está deshabilitado si no hay plantilla */}
              <Upload className="h-4 w-4 mr-2" />
              Ir a Cargar Lista de Precios
            </Button>
          </Link>
          
          {!proveedor.plantilla_mapeo && (
              <p className="text-xs text-amber-600 mt-2">
                  <strong>Botón deshabilitado:</strong> Necesitas crear y guardar una plantilla primero.
              </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}