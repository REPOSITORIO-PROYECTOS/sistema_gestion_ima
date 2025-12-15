"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import * as z from "zod";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/authStore";
import { API_CONFIG } from "@/lib/api-config";


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
    setIsLoading(true);
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
        setIsLoading(false);
    }
  }, [token, empresaId, form]);

  React.useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  // Envío omitido en esta versión mínima

  if (isLoading && !form.formState.isDirty) {
      return <p className="p-6 text-center text-muted-foreground">Cargando formulario de configuración...</p>;
  }

  return null;
}
