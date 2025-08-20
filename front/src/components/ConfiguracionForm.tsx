"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import * as z from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage, FormDescription } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/authStore";
import { AfipToolsPanel } from "./AfipToolsPanel";

// Schema de Zod para el formulario (sin cambios)
const formSchema = z.object({
  nombre_negocio: z.string().min(1, "Requerido").nullable(),
  direccion_negocio: z.string().optional().nullable(),
  telefono_negocio: z.string().optional().nullable(),
  mail_negocio: z.string().email("Debe ser un email válido.").optional().or(z.literal("")).nullable(),
  cuit: z.string().length(11, "CUIT debe tener 11 dígitos.").optional().nullable(),
  afip_punto_venta_predeterminado: z.string().min(1, "Requerido.").max(5, "Máximo 5 dígitos.").optional().nullable(),
  afip_condicion_iva: z.string().optional().nullable(), 
  link_google_sheets: z.string().optional().nullable(),
});

// Inferimos el tipo para los valores del formulario
type FormValues = z.infer<typeof formSchema>;

interface Props {
  empresaId: number;
}

export function ConfiguracionForm({ empresaId }: Props) {
  const token = useAuthStore((state) => state.token);
  const [isLoading, setIsLoading] = React.useState(true);
  
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
        nombre_negocio: "",
        direccion_negocio: "",
        telefono_negocio: "",
        mail_negocio: "",
        cuit: "",
        afip_punto_venta_predeterminado: "",
        afip_condicion_iva: "",
        link_google_sheets: "",
    },
  });

  // --- LÓGICA REFACTORIZADA Y CORREGIDA ---

const fetchConfig = React.useCallback(async () => {
    const { reset } = form; // Desestructuramos reset aquí adentro
    if (!token || !empresaId) return;
    setIsLoading(true);
    try {
        const API_URL = `https://sistema-ima.sistemataup.online/api/empresas/admin/${empresaId}/configuracion`;
        const res = await fetch(API_URL, { 
            headers: { Authorization: `Bearer ${token}` },
            cache: 'no-store'
        });
        if (!res.ok) throw new Error("No se pudo cargar la configuración de la empresa.");
        
        const data = await res.json();
        
        const transformedData = {
            ...data,
            cuit: data.cuit ? String(data.cuit) : "",
            afip_punto_venta_predeterminado: data.afip_punto_venta_predeterminado 
            ? String(data.afip_punto_venta_predeterminado) 
            : "",
        };
        
        reset(transformedData); // Usamos la función desestructurada

    } catch (err) {
        if (err instanceof Error) toast.error("Error al cargar datos", { description: err.message });
    } finally {
        setIsLoading(false);
    }
}, [token, empresaId, form]);

  React.useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const onSubmit = async (values: FormValues) => {
    setIsLoading(true);
    toast.info("Guardando cambios...");
    try {
      const API_URL = `https://sistema-ima.sistemataup.online/api/empresas/admin/${empresaId}/configuracion`;
      const res = await fetch(API_URL, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        const errorData = await res.json() as { detail: string };
        throw new Error(errorData.detail || "Error al guardar los cambios.");
      }
      toast.success("Configuración guardada con éxito.");
      
      // Se resincroniza el formulario con los datos actualizados del servidor
      await fetchConfig();

    } catch (err) {
      if (err instanceof Error) toast.error("Error al guardar", { description: err.message });
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && !form.formState.isDirty) {
      return <p>Cargando formulario de configuración...</p>;
  }

  return (
    <div className="space-y-12">
      {/* --- SECCIÓN 1: Formulario de Configuración General --- */}
      <div>
        <h3 className="text-xl text-green-950 font-semibold border-b pb-2 mb-6">Configuración General del Negocio</h3>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="space-y-4">
                <FormField control={form.control} name="nombre_negocio" render={({ field }) => (
                    <FormItem><FormLabel>Nombre del Negocio</FormLabel><FormControl><Input {...field} value={field.value ?? ''} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="direccion_negocio" render={({ field }) => (
                    <FormItem><FormLabel>Dirección</FormLabel><FormControl><Input {...field} value={field.value ?? ''} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="telefono_negocio" render={({ field }) => (
                    <FormItem><FormLabel>Teléfono</FormLabel><FormControl><Input {...field} value={field.value ?? ''} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="mail_negocio" render={({ field }) => (
                    <FormItem><FormLabel>Email</FormLabel><FormControl><Input type="email" {...field} value={field.value ?? ''} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="cuit" render={({ field }) => (
                    <FormItem><FormLabel>CUIT</FormLabel><FormControl><Input {...field} value={field.value ?? ''} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="afip_condicion_iva" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Condición frente al IVA</FormLabel>
                    <FormControl>
                      <Input {...field} value={field.value ?? ''} placeholder="Ej. Responsable Inscripto" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <FormField control={form.control} name="afip_punto_venta_predeterminado" render={({ field }) => (
                    <FormItem><FormLabel>Punto de Venta</FormLabel><FormControl><Input {...field} value={field.value ?? ''} /></FormControl><FormMessage /></FormItem>
                )} />
                <FormField control={form.control} name="link_google_sheets" render={({ field }) => (
                    <FormItem>
                        <FormLabel>ID Hoja de Google Sheets (Opcional)</FormLabel>
                        <FormControl><Input {...field} value={field.value ?? ''} placeholder="ID de la hoja para reportes..." /></FormControl>
                        <FormDescription>Conecta la empresa con su hoja de reportes automatizados.</FormDescription>
                        <FormMessage />
                    </FormItem>
                )} />
            </div>
            <div className="flex justify-end">
                <Button type="submit" disabled={isLoading || form.formState.isSubmitting}>
                    {isLoading ? "Actualizando..." : "Guardar Cambios Generales"}
                </Button>
            </div>
          </form>
        </Form>
      </div>

      {/* --- SECCIÓN 2: Panel Integrado de Herramientas AFIP --- */}
      <div>
        <h3 className="text-xl text-green-950 font-semibold border-b pb-2 mb-6">Herramientas Fiscales (AFIP)</h3>
        <AfipToolsPanel empresaId={empresaId} />
      </div>
    </div>
  );
}