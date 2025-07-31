"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import * as z from "zod";

import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/authStore";

// ====================================================================
// 1. EL SCHEMA DE ZOD (CONTRATO DE DATOS)
// Alineado 100% con tus schemas de Pydantic del backend.
// ====================================================================
const formSchema = z.object({
  nombre_negocio: z.string().min(1, "El nombre del negocio es requerido.").nullable(),
  color_principal: z.string().optional().nullable(),
  afip_condicion_iva: z.string().optional().nullable(),
  afip_punto_venta_predeterminado: z.number().int().positive().optional().nullable(),
  direccion_negocio: z.string().optional().nullable(),
  telefono_negocio: z.string().optional().nullable(),
  mail_negocio: z.string().email("Debe ser un email válido.").optional().nullable(),
  // Estos campos son de solo lectura en el formulario, se actualizan por separado
  ruta_logo: z.string().optional().nullable(),
  ruta_icono: z.string().optional().nullable(),
});

type FormValues = z.infer<typeof formSchema>;


// ====================================================================
// 2. EL COMPONENTE DE LA PÁGINA
// ====================================================================
export default function ConfiguracionPage() {
  const token = useAuthStore((state) => state.token);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      nombre_negocio: "",
      color_principal: "",
      afip_condicion_iva: "",
      direccion_negocio: "",
      telefono_negocio: "",
      mail_negocio: "",
    },
  });

  // URL CORRECTA Y FINAL para el endpoint
  const API_URL = "https://sistema-ima.sistemataup.online/api/configuracion/mi-empresa";

  const fetchConfig = React.useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(API_URL, { // <-- USANDO LA URL CORRECTA
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
          if (res.status === 404) {
              console.warn("No se encontró configuración existente para esta empresa.");
              // No es un error fatal, simplemente se mostrará un formulario vacío.
          } else {
              throw new Error("No se pudo obtener la configuración del servidor.");
          }
      } else {
        const result = await res.json();
        console.log("Datos recibidos de la API:", result);
        form.reset(result);
      }
    } catch (err) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [token, form]);

  React.useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const onSubmit = async (values: FormValues) => {
    if (!token) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await fetch(API_URL, { // <-- USANDO LA URL CORRECTA
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "El servidor rechazó los cambios.");
      }
      alert("Configuración guardada con éxito.");
    } catch (err) {
      if (err instanceof Error) alert(`Error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) return <p className="text-center p-8">Cargando configuración...</p>;

  return (
    <div className="max-w-4xl mx-auto p-4 md:p-6">
      <h1 className="text-2xl font-bold mb-6">Configuración de la Empresa</h1>
      {error && <p className="mb-4 bg-red-100 border-l-4 border-red-500 text-red-700 p-4" role="alert">{error}</p>}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
          
          {/* USAMOS LOS NOMBRES DE CAMPO CORRECTOS DEL BACKEND */}
          <FormField
            control={form.control}
            name="nombre_negocio"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Nombre del Negocio</FormLabel>
                <FormControl><Input placeholder="Mi Negocio S.A." {...field} value={field.value ?? ''} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="direccion_negocio"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Dirección</FormLabel>
                <FormControl><Input placeholder="Av. Siempre Viva 742" {...field} value={field.value ?? ''} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="telefono_negocio"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Teléfono</FormLabel>
                <FormControl><Input placeholder="+54 9 261 123-4567" {...field} value={field.value ?? ''} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          
          <FormField
            control={form.control}
            name="mail_negocio"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email de Contacto</FormLabel>
                <FormControl><Input type="email" placeholder="contacto@minegocio.com" {...field} value={field.value ?? ''} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Puedes añadir los otros campos (afip_condicion_iva, etc.) siguiendo el mismo patrón */}

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Guardando..." : "Guardar Cambios"}
          </Button>
        </form>
      </Form>
    </div>
  );
}