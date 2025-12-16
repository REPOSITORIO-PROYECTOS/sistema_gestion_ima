"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import * as z from "zod";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/authStore";
import { API_CONFIG } from "@/lib/api-config";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import * as Switch from "@radix-ui/react-switch";

type Articulo = {
  id: string;
  nombre: string;
};

const opcionesCondicionIVA = [
  "RESPONSABLE_INSCRIPTO",
  "EXENTO",
  "CONSUMIDOR_FINAL",
  "MONOTRIBUTO",
  "NO_CATEGORIZADO",
] as const;

const formSchema = z.object({
  nombre_negocio: z.string().min(1, "Requerido").nullable(),
  direccion_negocio: z.string().optional().nullable(),
  telefono_negocio: z.string().optional().nullable(),
  mail_negocio: z.string().email("Debe ser un email válido.").optional().or(z.literal("")).nullable(),
  cuit: z.string().length(11, "CUIT debe tener 11 dígitos.").optional().nullable(),
  afip_punto_venta_predeterminado: z.string().min(1, "Requerido.").max(5, "Máximo 5 dígitos.").optional().nullable(),
  afip_condicion_iva: z.enum(opcionesCondicionIVA, {
    required_error: "Debe seleccionar una condición de IVA.",
}).nullable(),
  link_google_sheets: z.string().optional().nullable(),
  aclaraciones_legales: z.record(z.string()).optional(),
  balanza_articulo_id: z.string().optional(),
  balanza_auto_agregar: z.boolean().optional(),
  balanza_auto_facturar: z.boolean().optional(),
  balanza_precio_fuente: z.enum(["producto", "evento"]).optional(),
});

type FormValues = z.infer<typeof formSchema>;

interface Props {
  empresaId: number;
  sections?: {
    general?: boolean;
    balanza?: boolean;
    afip?: boolean;
  };
}

export const ConfiguracionForm = (props: Props) => {
  const { empresaId } = props;
  const token = useAuthStore((state) => state.token);
  const [articulos, setArticulos] = React.useState<Articulo[]>([]);

  React.useEffect(() => {
    const fetchArticulos = async () => {
      if (!token) return;
      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}/articulos/obtener_todos`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Error al cargar artículos.");
        const data: Articulo[] = await res.json();
        setArticulos(data.map(p => ({id: String(p.id), nombre: p.nombre ?? ""})));
      } catch (err) {
        console.error("Error al obtener artículos:", err);
        toast.error("Error al cargar artículos para balanza.");
      }
    };
    fetchArticulos();
  }, [token]);
  
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
        nombre_negocio: "",
        direccion_negocio: "",
        telefono_negocio: "",
        mail_negocio: "",
        cuit: "",
        afip_punto_venta_predeterminado: "",
        afip_condicion_iva: null,
        link_google_sheets: "",
        aclaraciones_legales: {},
        balanza_articulo_id: "",
        balanza_auto_agregar: false,
        balanza_auto_facturar: false,
        balanza_precio_fuente: "producto",
    },
  });

  // --- Lógica de carga y envío (sin cambios) ---
  const fetchConfig = React.useCallback(async () => {
    const { reset } = form;
    if (!token || !empresaId) return;
    try {
        const API_URL = `${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`;
        const res = await fetch(API_URL, { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store' });
        if (!res.ok) throw new Error("No se pudo cargar la configuración.");
        
        const data = await res.json();
        const transformedData = {
            ...data,
            cuit: data.cuit ? String(data.cuit) : "",
            afip_punto_venta_predeterminado: data.afip_punto_venta_predeterminado ? String(data.afip_punto_venta_predeterminado) : "",
            aclaraciones_legales: data.aclaraciones_legales ?? {},
            balanza_articulo_id: data.aclaraciones_legales?.balanza_articulo_id ?? "",
            balanza_auto_agregar: (data.aclaraciones_legales?.balanza_auto_agregar ?? "false") === "true",
            balanza_auto_facturar: (data.aclaraciones_legales?.balanza_auto_facturar ?? "false") === "true",
            balanza_precio_fuente: (data.aclaraciones_legales?.balanza_precio_fuente ?? "producto"),
        };
        reset(transformedData);
    } catch (err) {
        if (err instanceof Error) toast.error("Error al cargar datos", { description: err.message });
    } finally {
    }
  }, [token, empresaId, form]);

  React.useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  // Envío omitido en esta versión mínima

  async function onSubmit(values: FormValues) {
    if (!token || !empresaId) {
      toast.error("Error de autenticación o empresa no seleccionada.");
      return;
    }
    try {
      const API_URL = `${API_CONFIG.BASE_URL}/empresas/admin/${empresaId}/configuracion`;
      const payload = {
        ...values,
        cuit: values.cuit === "" ? null : values.cuit,
        afip_punto_venta_predeterminado: values.afip_punto_venta_predeterminado === "" ? null : Number(values.afip_punto_venta_predeterminado),
        aclaraciones_legales: {
          ...values.aclaraciones_legales,
          balanza_articulo_id: values.balanza_articulo_id || null,
          balanza_auto_agregar: String(values.balanza_auto_agregar),
          balanza_auto_facturar: String(values.balanza_auto_facturar),
          balanza_precio_fuente: values.balanza_precio_fuente || "producto",
        },
      };

      const res = await fetch(API_URL, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Error al guardar la configuración.");
      }

      toast.success("Configuración guardada correctamente.");
      form.reset(values); // Resetear el formulario con los valores guardados
    } catch (err) {
      if (err instanceof Error) toast.error("Error al guardar", { description: err.message });
    } finally {
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 p-4">
        {/* Sección General */}
        {props.sections?.general && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-green-950">Configuración General</h2>
            <FormField
              control={form.control}
              name="nombre_negocio"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nombre del Negocio</FormLabel>
                  <FormControl>
                    <Input placeholder="Nombre de tu negocio" {...field} value={field.value || ""} />
                  </FormControl>
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
                  <FormControl>
                    <Input placeholder="Dirección del negocio" {...field} value={field.value || ""} />
                  </FormControl>
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
                  <FormControl>
                    <Input placeholder="Teléfono del negocio" {...field} value={field.value || ""} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="mail_negocio"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input placeholder="Email del negocio" {...field} value={field.value || ""} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="link_google_sheets"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Link Google Sheets</FormLabel>
                  <FormControl>
                    <Input placeholder="Link a tu hoja de cálculo de Google" {...field} value={field.value || ""} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        )}

        {/* Sección AFIP */}
        {props.sections?.afip && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-green-950">Configuración AFIP</h2>
            <FormField
              control={form.control}
              name="cuit"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>CUIT</FormLabel>
                  <FormControl>
                    <Input placeholder="CUIT de la empresa" {...field} value={field.value || ""} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="afip_condicion_iva"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Condición IVA</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value || undefined}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona condición de IVA" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {opcionesCondicionIVA.map((opcion) => (
                        <SelectItem key={opcion} value={opcion}>
                          {opcion.replace(/_/g, " ")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="afip_punto_venta_predeterminado"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Punto de Venta Predeterminado</FormLabel>
                  <FormControl>
                    <Input type="number" placeholder="Ej: 1, 2, 3" {...field} value={field.value || ""} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        )}

        {/* Sección Balanza */}
        {props.sections?.balanza && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-green-950">Configuración Balanza</h2>
            <FormField
              control={form.control}
              name="balanza_articulo_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Artículo para Balanza</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value || ""}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona un artículo" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {articulos.map((articulo) => (
                        <SelectItem key={articulo.id} value={articulo.id}>
                          {articulo.nombre}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="balanza_auto_agregar"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                  <div className="space-y-0.5">
                    <FormLabel>Auto Agregar a Venta</FormLabel>
                    <FormDescription>
                      Si está activo, el artículo de balanza se agregará automáticamente al escanear.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch.Root
                      checked={field.value}
                      onCheckedChange={field.onChange}
                      className="w-[42px] h-[25px] bg-gray-300 rounded-full relative data-[state=checked]:bg-green-500 outline-none cursor-default"
                    >
                      <Switch.Thumb className="block w-[21px] h-[21px] bg-white rounded-full shadow-[0_2px_2px] shadow-blackA7 transition-transform duration-100 translate-x-0.5 will-change-transform data-[state=checked]:translate-x-[19px]" />
                    </Switch.Root>
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="balanza_auto_facturar"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                  <div className="space-y-0.5">
                    <FormLabel>Auto Facturar</FormLabel>
                    <FormDescription>
                      Si está activo, la venta de balanza se facturará automáticamente.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch.Root
                      checked={field.value}
                      onCheckedChange={field.onChange}
                      className="w-[42px] h-[25px] bg-gray-300 rounded-full relative data-[state=checked]:bg-green-500 outline-none cursor-default"
                    >
                      <Switch.Thumb className="block w-[21px] h-[21px] bg-white rounded-full shadow-[0_2px_2px] shadow-blackA7 transition-transform duration-100 translate-x-0.5 will-change-transform data-[state=checked]:translate-x-[19px]" />
                    </Switch.Root>
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="balanza_precio_fuente"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Fuente de Precio Balanza</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value || undefined}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona la fuente de precio" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="producto">Precio de Producto</SelectItem>
                      <SelectItem value="evento">Precio de Evento (Pesada)</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        )}

        <Button type="submit" disabled={form.formState.isSubmitting || !form.formState.isDirty}>
          {form.formState.isSubmitting ? "Guardando..." : "Guardar Cambios"}
        </Button>
      </form>
    </Form>
  );
}
