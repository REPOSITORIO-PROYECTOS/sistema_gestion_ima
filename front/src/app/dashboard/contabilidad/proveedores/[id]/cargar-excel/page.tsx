"use client"; // Es crucial que sea un Client Component

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";

// Importamos los componentes hijos que usaremos
import { PlantillaGuia } from "./PlantillaGuia";
import { UploaderConVistaPrevia } from "./UploaderVistaPrevia";

// --- Definición de Tipos de Datos ---
// Esto define cómo se ven los datos que esperamos de la API

interface MapeoPlantilla {
  columna_excel: string;
  campo_db: string;
}

interface Proveedor {
  id: number;
  nombre_razon_social: string;
  // La plantilla viene anidada dentro del proveedor. Es opcional.
  plantilla_mapeo?: {
    mapeos: MapeoPlantilla[];
  };
}

export default function ActualizarPreciosPage() {
  const params = useParams();
  const token = useAuthStore((state) => state.token);

  // Normalizamos el ID de la URL
  const proveedorIdString = Array.isArray(params.id) ? params.id[0] : params.id;
  const proveedorId = Number(proveedorIdString);

  const [proveedor, setProveedor] = useState<Proveedor | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://sistema-ima.sistemataup.online";

  useEffect(() => {
    const fetchProveedorData = async () => {
      if (!token || !proveedorId || isNaN(proveedorId)) {
        setIsLoading(false);
        if (isNaN(proveedorId)) toast.error("El ID del proveedor en la URL no es válido.");
        return;
      }
      
      setIsLoading(true);
      try {
        const response = await fetch(`${API_URL}/api/proveedores/${proveedorId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!response.ok) {
          throw new Error("No se pudieron cargar los datos del proveedor.");
        }

        const proveedorData: Proveedor = await response.json();
        setProveedor(proveedorData);
        
      } catch (error) {
        if (error instanceof Error) {
          toast.error("Error al cargar datos", { description: error.message });
        }
      } finally {
        setIsLoading(false);
      }
    };
    fetchProveedorData();
  }, [proveedorId, token, API_URL]);

  if (isLoading) {
    return <p className="p-4 text-center text-muted-foreground">Cargando datos del proveedor...</p>;
  }

  if (!proveedor) {
    return <p className="p-4 text-center text-red-500">No se encontraron los datos del proveedor.</p>;
  }

  // --- El punto CLAVE de la conexión ---
  // Extraemos los mapeos de la plantilla del proveedor. Si no existen, usamos un array vacío.
  const plantillaData = proveedor.plantilla_mapeo?.mapeos || [];

  return (
    <div className="p-4 md:p-6 space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-bold">Actualización de Lista de Precios</h1>
        <p className="text-muted-foreground">
          Proveedor: <span className="font-semibold text-primary">{proveedor.nombre_razon_social}</span>
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">1. Guía de la Plantilla</h2>
          {/* 
            Aquí está la corrección: Le pasamos el dato 'plantillaData'
            a través de una prop llamada 'plantilla', que es el nombre que el hijo espera.
          */}
          <PlantillaGuia plantilla={plantillaData} />
        </div>
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">2. Cargar Archivo y Vista Previa</h2>
          {/* Este componente también recibe sus props correctamente */}
          <UploaderConVistaPrevia proveedorId={proveedorId} token={token} API_URL={API_URL} />
        </div>
      </div>
    </div>
  );
}