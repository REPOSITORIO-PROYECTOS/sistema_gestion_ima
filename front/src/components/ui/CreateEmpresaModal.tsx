"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/lib/authStore";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";

const formSchema = z.object({
  nombre_legal: z.string().min(1, "El nombre legal es requerido."),
  nombre_fantasia: z.string().min(1, "El nombre de fantasía es requerido."),
  cuit: z.string().length(11, "El CUIT debe tener exactamente 11 dígitos."),
});

type FormValues = z.infer<typeof formSchema>;

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function CreateEmpresaModal({ isOpen, onClose, onSuccess }: Props) {
  const token = useAuthStore((state) => state.token);
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { nombre_legal: "", nombre_fantasia: "", cuit: "" },
  });

  const onSubmit = async (values: FormValues) => {
    if (!token) return;
    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/empresas/admin/crear", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(values),
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error al crear la empresa.");
      }
      alert("Empresa creada con éxito.");
      onSuccess();
    } catch (err) {
      if (err instanceof Error) alert(`Error: ${err.message}`);
    }
  };
  
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-card p-6 rounded-lg shadow-xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-xl font-bold mb-4">Crear Nueva Empresa</h2>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField control={form.control} name="nombre_legal" render={({ field }) => (
              <FormItem><FormLabel>Nombre Legal</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="nombre_fantasia" render={({ field }) => (
              <FormItem><FormLabel>Nombre Fantasía</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="cuit" render={({ field }) => (
              <FormItem><FormLabel>CUIT (sin guiones)</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Creando..." : "Crear Empresa"}
              </Button>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
}