"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import ExcelUploader from "./ExcelUploader";
import { Proveedor } from "../proveedores/columns";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";

// Importamos el componente para mostrar la previsualización y su tipo de datos
import { PreviewChanges, type PrevisualizacionResponse } from "@/components/PreviewChanges";

interface Props {
  proveedor: Proveedor;
  onUploadComplete: () => void; // Prop para notificar a la página principal que debe recargar
}

export const ProveedorExcelUpload: React.FC<Props> = ({ proveedor, onUploadComplete }) => {
  // --- ESTADOS DEL COMPONENTE ---
  const [open, setOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  // Estado para guardar la respuesta de previsualización del backend
  const [previewData, setPreviewData] = useState<PrevisualizacionResponse | null>(null);
  const { token } = useAuthStore();

  // --- MANEJADORES DE LÓGICA ---

  /**
   * Se ejecuta cuando el usuario selecciona un archivo en el componente ExcelUploader.
   * Llama al endpoint de previsualización.
   */
  const handleFileSelect = async (file: File) => {
    setIsLoading(true);
    toast.info("Procesando archivo...", { description: "Generando previsualización de cambios." });

    const formData = new FormData();
    formData.append("archivo", file);

    try {
      const res = await fetch(`https://sistema-ima.sistemataup.online/api/importaciones/preview/${proveedor.id}`, {
        method: "POST",
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error del servidor al procesar el archivo.");
      }

      const data: PrevisualizacionResponse = await res.json();
      setPreviewData(data); // Guardamos la respuesta para mostrar el siguiente paso
      toast.success("Previsualización lista.", { description: data.resumen });

    } catch (error) {
      if (error instanceof Error) {
        toast.error("Fallo al previsualizar", { description: error.message });
      }
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Se ejecuta cuando el usuario hace clic en el botón "Confirmar Cambios".
   * Llama al endpoint de confirmación.
   */
  const handleConfirm = async () => {
    if (!previewData?.articulos_a_actualizar) return;

    setIsLoading(true);
    toast.info("Confirmando y aplicando cambios...", { description: "Esto puede tardar unos segundos." });

    try {
      const res = await fetch(`https://sistema-ima.sistemataup.online/api/importaciones/confirmar`, {
        method: "POST",
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          articulos_a_actualizar: previewData.articulos_a_actualizar
        })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error al confirmar los cambios.");
      }

      const result = await res.json();
      toast.success("¡Precios Actualizados!", { description: result.message });
      
      onUploadComplete(); // ¡Éxito! Le decimos a la página principal que recargue sus datos.
      handleClose(); // Cierra y resetea el modal

    } catch (error) {
      if (error instanceof Error) {
        toast.error("Fallo al confirmar", { description: error.message });
      }
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Cierra el diálogo y resetea su estado para la próxima vez que se abra.
   */
  const handleClose = () => {
    setOpen(false);
    // Añadimos un pequeño retardo para que la transición de cierre sea suave
    // antes de que el contenido desaparezca.
    setTimeout(() => {
        setPreviewData(null);
        setIsLoading(false);
    }, 300);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">📄 Cargar Lista</Button>
      </DialogTrigger>

      <DialogContent className="max-w-4xl" onInteractOutside={handleClose}>
        <DialogHeader>
          <DialogTitle>Actualizar Precios para: {proveedor.nombre_razon_social}</DialogTitle>
          <DialogDescription>
            {/* El subtítulo cambia dependiendo del paso en el que estemos */}
            {previewData 
              ? "Revisa los cambios detectados. Los precios se actualizarán solo después de tu confirmación."
              : "Sube la lista de precios en formato Excel. El sistema la comparará con los datos actuales."
            }
          </DialogDescription>
        </DialogHeader>
        
        {/* --- VISTA CONDICIONAL: UPLOADER O PREVISUALIZACIÓN --- */}
        {previewData ? (
          <PreviewChanges 
            data={previewData} 
            isLoading={isLoading}
            onConfirm={handleConfirm}
            onCancel={() => setPreviewData(null)} // El botón "Cancelar" permite volver al paso de subida
          />
        ) : (
          <ExcelUploader 
            onFileSelect={handleFileSelect} 
            isLoading={isLoading} // Le pasamos el estado de carga al uploader
          />
        )}
      </DialogContent>
    </Dialog>
  );
};