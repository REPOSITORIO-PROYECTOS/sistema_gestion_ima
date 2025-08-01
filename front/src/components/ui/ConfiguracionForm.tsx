"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/authStore";

// El schema de Zod no cambia
const formSchema = z.object({
  nombre_negocio: z.string().min(1, "Requerido").nullable(),
  direccion_negocio: z.string().optional().nullable(),
  telefono_negocio: z.string().optional().nullable(),
  mail_negocio: z.string().email().optional().nullable(),
  cuit: z.string().min(11, "CUIT inválido").max(11, "CUIT inválido").optional().nullable(),
  punto_venta: z.string().min(1, "Requerido").optional().nullable(),
});

type FormValues = z.infer<typeof formSchema>;

// El componente ahora acepta el ID de la empresa como prop
interface Props {
  empresaId: number;
}

export function ConfiguracionForm({ empresaId }: Props) {
  const token = useAuthStore((state) => state.token);
  const [isLoading, setIsLoading] = React.useState(true);
  const form = useForm<FormValues>({ resolver: zodResolver(formSchema) });

  // La URL ahora es dinámica y usa el endpoint de admin
  const API_URL = `https://sistema-ima.sistemataup.online/api/empresas/admin/${empresaId}/configuracion`;

  React.useEffect(() => {
    const fetchConfig = async () => {
      if (!token) return;
      setIsLoading(true);
      try {
        const res = await fetch(API_URL, { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok) throw new Error("No se pudo cargar la configuración para esta empresa.");
        const data = await res.json();
        form.reset(data); // Rellena el formulario con los datos
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchConfig();
  }, [token, empresaId, form, API_URL]);

  const onSubmit = async (values: FormValues) => {
    try {
      const res = await fetch(API_URL, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(values),
      });
      if (!res.ok) throw new Error("Error al guardar los cambios.");
      alert("Configuración guardada con éxito.");
    } catch (err) {
      if (err instanceof Error) alert(err.message);
    }
  };

  if (isLoading) return <p>Cargando formulario de configuración...</p>;

  // El JSX del formulario es el mismo que ya tenías
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        {/* Aquí van todos los FormField como ya los tenías */}
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
            <FormItem><FormLabel>Email</FormLabel><FormControl><Input {...field} value={field.value ?? ''} /></FormControl><FormMessage /></FormItem>
        )} />
        <FormField control={form.control} name="cuit" render={({ field }) => (
            <FormItem><FormLabel>CUIT</FormLabel><FormControl><Input {...field} value={field.value ?? ''} /></FormControl><FormMessage /></FormItem>
        )} />
        <FormField control={form.control} name="punto_venta" render={({ field }) => (
            <FormItem><FormLabel>Punto de Venta</FormLabel><FormControl><Input {...field} value={field.value ?? ''} /></FormControl><FormMessage /></FormItem>
        )} />
        {/* Aquí puedes añadir más campos según sea necesario */}
        {/* ... etc ... */}
        <Button type="submit" disabled={form.formState.isSubmitting}>
            {form.formState.isSubmitting ? "Guardando..." : "Guardar Cambios"}
        </Button>
      </form>
    </Form>
  );
}