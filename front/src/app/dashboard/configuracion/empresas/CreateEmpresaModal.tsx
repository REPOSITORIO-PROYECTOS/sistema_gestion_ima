"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage, FormDescription } from "@/components/ui/form";

// ====================================================================
// === CORRECCIÓN 1: Añadimos 'id_google_sheets' al schema simple ===
// ====================================================================
const formSchema = z.object({
  nombre_legal: z.string().min(1, "El nombre legal es requerido."),
  cuit: z.string().length(11, "El CUIT debe tener exactamente 11 dígitos sin guiones."),
  nombre_fantasia: z.string().optional(),
  id_google_sheets: z.string().optional(), // Campo opcional
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
    // =====================================================================
    // === CORRECCIÓN 2: Añadimos el valor por defecto para el nuevo campo ===
    // =====================================================================
    defaultValues: {
      nombre_legal: "",
      cuit: "",
      nombre_fantasia: "",
      id_google_sheets: "",
    },
  });

  const onSubmit = async (values: FormValues) => {
    if (!token) return;
    toast.info("Creando empresa...");

    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/empresas/admin/crear", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        // `values` ahora incluye el id_google_sheets para ser enviado al backend
        body: JSON.stringify(values),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error al crear la empresa.");
      }

      toast.success("Empresa creada con éxito.");
      form.reset();
      onSuccess();

    } catch (err) {
      if (err instanceof Error) {
        toast.error("Fallo al crear la empresa", { description: err.message });
      }
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Crear Nueva Empresa</DialogTitle>
          <DialogDescription>
            Ingresa los datos legales básicos. La configuración detallada se realiza después.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 py-4">
            <FormField control={form.control} name="nombre_legal" render={({ field }) => (
              <FormItem><FormLabel>Nombre Legal</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="cuit" render={({ field }) => (
              <FormItem><FormLabel>CUIT (sin guiones)</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="nombre_fantasia" render={({ field }) => (
              <FormItem><FormLabel>Nombre Fantasía (Opcional)</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage />
            </FormItem>
            )} />
            
            {/* =================================================================== */}
            {/* === CORRECCIÓN 3: Añadimos el FormField para el ID de Sheets === */}
            {/* =================================================================== */}
            <FormField control={form.control} name="id_google_sheets" render={({ field }) => (
              <FormItem>
                <FormLabel>ID Hoja de Google Sheets (Opcional)</FormLabel>
                <FormControl><Input {...field} placeholder="ID de la hoja para reportes..."/></FormControl>
                <FormDescription>
                  Este ID se usará para los reportes automatizados.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )} />

            <DialogFooter className="pt-4">
              <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Creando..." : "Crear Empresa"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}