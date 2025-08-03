"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useAuthStore } from "@/lib/authStore";
import { toast } from "sonner";

// Importaciones de componentes de ShadCN/UI
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";

// 1. Schema Zod unificado con todos los campos de empresa, configuración y admin
const formSchema = z.object({
  // --- Datos Legales ---
  nombre_legal: z.string().min(1, "El nombre legal es requerido."),
  cuit: z.string().length(11, "El CUIT debe tener exactamente 11 dígitos sin guiones."),
  
  // --- Datos de Configuración ---
  nombre_fantasia: z.string().optional(),
  direccion_negocio: z.string().optional(),
  telefono_negocio: z.string().optional(),
  mail_negocio: z.string().email("Debe ser un email válido.").optional().or(z.literal("")),
  afip_punto_venta_predeterminado: z.coerce.number({invalid_type_error: "Debe ser un número"}).positive("Debe ser un número positivo").optional(),
  afip_condicion_iva: z.enum([
    "Responsable Inscripto",
    "Monotributista",
    "Exento",
  ], { required_error: "La condición fiscal es requerida." }),
  link_sheets: z.string().optional(),
  
  // --- Datos Primer Administrador ---
  admin_username: z.string().min(4, "El nombre de usuario debe tener al menos 4 caracteres."),
  admin_password: z.string().min(6, "La contraseña debe tener al menos 6 caracteres."),
  admin_password_confirm: z.string(),
}).refine(data => data.admin_password === data.admin_password_confirm, {
  message: "Las contraseñas no coinciden.",
  path: ["admin_password_confirm"],
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
    // 2. Valores por defecto para todos los campos
    defaultValues: {
      nombre_legal: "",
      cuit: "",
      nombre_fantasia: "",
      direccion_negocio: "",
      telefono_negocio: "",
      mail_negocio: "",
      afip_punto_venta_predeterminado: undefined,
      afip_condicion_iva: "Responsable Inscripto",
      link_sheets: "",
      admin_username: "",
      admin_password: "",
      admin_password_confirm: "",
    },
  });

  const onSubmit = async (values: FormValues) => {
    if (!token) return;
    toast.info("Creando empresa y configurando...");

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

      toast.success("Empresa creada y configurada con éxito.");
      form.reset();
      onSuccess();

    } catch (err) {
      if (err instanceof Error) {
        toast.error("Fallo en la creación", { description: err.message });
      }
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Crear y Configurar Nueva Empresa</DialogTitle>
          <DialogDescription>
            Completa todos los datos para registrar y configurar la empresa en un solo paso.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 py-4 max-h-[70vh] overflow-y-auto pr-6">
            
            <h3 className="text-md font-semibold text-muted-foreground pt-2">Datos de la Empresa</h3>
            <FormField control={form.control} name="nombre_legal" render={({ field }) => (
              <FormItem><FormLabel>Nombre Legal</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="cuit" render={({ field }) => (
              <FormItem><FormLabel>CUIT (sin guiones)</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="nombre_fantasia" render={({ field }) => (
              <FormItem><FormLabel>Nombre Fantasía (Opcional)</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="direccion_negocio" render={({ field }) => (
              <FormItem><FormLabel>Dirección (Opcional)</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />

            {/* --- REEMPLAZO DEL SEPARADOR --- */}
            <div className="border-b my-6" />
            
            <h3 className="text-md font-semibold text-muted-foreground">Configuración Fiscal y Reportes</h3>
             <FormField control={form.control} name="afip_punto_venta_predeterminado" render={({ field }) => (
              <FormItem><FormLabel>Punto de Venta</FormLabel><FormControl><Input type="number" placeholder="Ej: 1" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
             <FormField control={form.control} name="afip_condicion_iva" render={({ field }) => (
              <FormItem>
                <FormLabel>Condición Fiscal</FormLabel>
                <Select onValueChange={field.onChange} defaultValue={field.value}>
                  <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                  <SelectContent>
                    <SelectItem value="Responsable Inscripto">Responsable Inscripto</SelectItem>
                    <SelectItem value="Monotributista">Monotributista</SelectItem>
                    <SelectItem value="Exento">Exento</SelectItem>
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="link_sheets" render={({ field }) => (
              <FormItem>
                <FormLabel>ID de Hoja de Google Sheets (Opcional)</FormLabel>
                <FormControl><Input {...field} /></FormControl>
              </FormItem>
            )} />

            {/* --- REEMPLAZO DEL SEPARADOR --- */}
            <div className="border-b my-6" />

            <h3 className="text-md font-semibold text-muted-foreground">Primer Administrador</h3>
            <FormField control={form.control} name="admin_username" render={({ field }) => (
              <FormItem><FormLabel>Nombre de Usuario</FormLabel><FormControl><Input {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="admin_password" render={({ field }) => (
              <FormItem><FormLabel>Contraseña</FormLabel><FormControl><Input type="password" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            <FormField control={form.control} name="admin_password_confirm" render={({ field }) => (
              <FormItem><FormLabel>Confirmar Contraseña</FormLabel><FormControl><Input type="password" {...field} /></FormControl><FormMessage /></FormItem>
            )} />
            
            <DialogFooter className="pt-4">
              <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Procesando..." : "Crear Empresa"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}