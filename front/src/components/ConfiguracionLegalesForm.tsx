// src/components/ConfiguracionLegalesForm.tsx

'use client';

import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://sistema-ima.sistemataup.online";

// Definimos los tipos de comprobantes que tendrán textos legales
const TIPOS_COMPROBANTE = ["factura", "remito", "presupuesto", "recibo"];

export function ConfiguracionLegalesForm() {
  const token = useAuthStore((state) => state.token);
  
  // Estado para guardar los textos. Usamos un objeto: { factura: "...", remito: "..." }
  const [textos, setTextos] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(true);

  // Efecto para cargar los datos iniciales cuando el componente se monta
  useEffect(() => {
    if (!token) return;

    const fetchTextosLegales = async () => {
      setIsFetching(true);
      try {
        const res = await fetch(`${API_URL}/api/configuracion/mi-empresa`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("No se pudieron cargar los textos legales.");
        
        const data = await res.json();
        // Guardamos las aclaraciones que vienen de la BD, o un objeto vacío si no hay
        setTextos(data.aclaraciones_legales || {});

      } catch (error) {
        console.error("Error al obtener textos:", error);
        toast.error("Error al cargar la configuración de textos legales.");
      } finally {
        setIsFetching(false);
      }
    };

    fetchTextosLegales();
  }, [token]);

  // Maneja los cambios en cualquier textarea
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setTextos(prev => ({ ...prev, [name]: value }));
  };

  // Maneja el envío del formulario
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!token) return;
    setIsLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/configuracion/mi-empresa`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          aclaraciones_legales: textos
        }),
      });

      if (!res.ok) throw new Error("Error al guardar los cambios.");
      
      toast.success("Textos legales actualizados correctamente.");

    } catch (error) {
      console.error("Error al guardar textos:", error);
      toast.error("Hubo un error al guardar los textos.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isFetching) {
    return <p>Cargando configuración de textos legales...</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-xl font-bold text-green-950">Aclaraciones Legales</h2>
        <p className="text-muted-foreground">
          Define los textos que se añadirán automáticamente al pie de cada tipo de comprobante.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {TIPOS_COMPROBANTE.map((tipo) => (
          <div key={tipo} className="space-y-2">
            <Label htmlFor={tipo} className="capitalize font-semibold text-gray-700">
              Texto para {tipo}
            </Label>
            <Textarea
              id={tipo}
              name={tipo}
              value={textos[tipo] || ""}
              onChange={handleChange}
              placeholder={`Ej: Este presupuesto tiene una validez de 15 días...`}
              className="min-h-[100px]"
              disabled={isLoading}
            />
          </div>
        ))}
      </div>
      
      <Button type="submit" disabled={isLoading} className="bg-green-900 text-white">
        {isLoading ? "Guardando..." : "Guardar Cambios en Textos Legales"}
      </Button>
    </form>
  );
}