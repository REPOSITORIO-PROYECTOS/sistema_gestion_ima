"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import * as React from "react";
import { useForm } from "react-hook-form";
import * as z from "zod";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/authStore";
import { API_CONFIG } from "@/lib/api-config";
import { attachAutoScaleBridge } from "@/lib/scaleSerial";
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
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import * as Switch from "@radix-ui/react-switch";

// ... (resto de imports y type Articulo)

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
  nombre_legal: z.string().optional().nullable(),
  nombre_fantasia: z.string().optional().nullable(),
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
  onSave?: () => void;
}

export const ConfiguracionForm = (props: Props) => {
  const { empresaId } = props;
  const token = useAuthStore((state) => state.token);
  const sections = {
    general: true,
    afip: true,
    balanza: true,
    ...props.sections,
  };
  const [articulos, setArticulos] = React.useState<Articulo[]>([]);
  const [testBalanzaData, setTestBalanzaData] = React.useState<string | null>(null);
  const [probandoBalanza, setProbandoBalanza] = React.useState(false);

  // Función para probar balanza
  const handleProbarBalanza = async (forzarSeleccion: boolean = false) => {
    if (!token) {
      toast.error("No hay token disponible");
      return;
    }

    setProbandoBalanza(true);
    setTestBalanzaData("Escuchando puertos... Coloque peso en la balanza.");

    try {
      // 1. Verificar si ya hay puertos autorizados
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const puertosExistentes = await (navigator.serial as any).getPorts();

      // 2. Si no hay puertos o se fuerza selección, pedir puerto
      if (puertosExistentes.length === 0 || forzarSeleccion) {
        try {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          await (navigator.serial as any).requestPort();
        } catch (e) {
          console.log("Selección de puerto cancelada o fallida", e);
          if (puertosExistentes.length === 0) {
            setTestBalanzaData("No se seleccionó ningún puerto. Intente nuevamente.");
            setProbandoBalanza(false);
            return;
          }
        }
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const bridge = await attachAutoScaleBridge(token, (data: any) => {
        console.log("TEST BALANZA DATA:", data);
        let mensaje = "";

        if (data?.peso) {
          mensaje = `✅ PESO DETECTADO: ${data.peso} kg\n`;
          if (data.precio) mensaje += `Precio: $${data.precio}\n`;
          mensaje += `\n(Datos procesados correctamente)`;
        } else if (data?.rawLine || data?.raw) {
          const raw = data.rawLine || data.raw;
          mensaje = `⚠️ DATOS CRUDOS RECIBIDOS (No se pudo extraer peso):\n"${raw}"\n`;
          mensaje += `\nEl sistema intentó buscar números pero no encontró un formato válido.`;
          mensaje += `\nAsegúrese de que la balanza envíe datos numéricos visibles.`;
        } else {
          mensaje = JSON.stringify(data, null, 2);
        }

        setTestBalanzaData(mensaje);
      });

      if (!bridge) {
        setTestBalanzaData("No se pudo conectar (Web Serial no soportado).");
        setProbandoBalanza(false);
        return;
      }

      // Desconectar automáticamente después de 30 segundos
      setTimeout(() => {
        bridge.stop();
        setProbandoBalanza(false);
        // Usar un ref o simplemente verificar si sigue el mensaje inicial, pero testBalanzaData es state y aquí puede ser stale.
        // Mejor simplemente seteamos un aviso si el usuario sigue esperando.
        setTestBalanzaData((prev) => {
          if (prev && prev.includes("Escuchando puertos")) {
            return "Tiempo de espera agotado sin recibir datos. Verifique conexión y encienda la balanza.";
          }
          return prev;
        });
      }, 30000);

    } catch (error) {
      console.error(error);
      setTestBalanzaData("Error al intentar conectar.");
      setProbandoBalanza(false);
    }
  };

  React.useEffect(() => {
    const fetchArticulos = async () => {
      if (!token) return;
      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}/articulos/obtener_todos`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Error al cargar artículos.");
        const data = await res.json() as { id: string | number; nombre?: string; descripcion?: string }[];
        // Mapeo seguro, intentando obtener nombre o descripcion
        const mapeados = data.map(p => ({
          id: String(p.id),
          nombre: p.nombre || p.descripcion || `Artículo #${p.id}`
        }));
        setArticulos(mapeados);
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
      nombre_legal: "",
      nombre_fantasia: "",
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
        nombre_legal: data.nombre_legal ?? "",
        nombre_fantasia: data.nombre_fantasia ?? "",
        cuit: data.cuit ? String(data.cuit) : "",
        afip_punto_venta_predeterminado: data.afip_punto_venta_predeterminado ? String(data.afip_punto_venta_predeterminado) : "",
        afip_condicion_iva: data.afip_condicion_iva ?? null,
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
        afip_condicion_iva: !values.afip_condicion_iva ? null : values.afip_condicion_iva,
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
      props.onSave?.();
    } catch (err) {
      if (err instanceof Error) toast.error("Error al guardar", { description: err.message });
    } finally {
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8 p-4">
        {/* Sección General */}
        {sections.general && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-green-950">Configuración General</h2>

            <FormField
              control={form.control}
              name="nombre_legal"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nombre Legal</FormLabel>
                  <FormControl>
                    <Input placeholder="Nombre legal de la empresa" {...field} value={field.value || ""} />
                  </FormControl>
                  <FormDescription>
                    El nombre legal registrado ante AFIP
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="nombre_fantasia"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nombre de Fantasía</FormLabel>
                  <FormControl>
                    <Input placeholder="Nombre de fantasía (cómo se conoce la empresa)" {...field} value={field.value || ""} />
                  </FormControl>
                  <FormDescription>
                    El nombre comercial con el que se conoce la empresa
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

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
        {sections.afip && (
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
                  <Select onValueChange={field.onChange} value={field.value || ""}>
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
        {sections.balanza && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-green-950">Configuración Balanza</h2>

            {/* Botón de Prueba */}
            <div className="p-4 border border-blue-200 bg-blue-50 rounded-md">
              <h3 className="font-semibold text-blue-800 mb-2">Prueba de Conexión</h3>
              <p className="text-sm text-blue-600 mb-4">
                Presiona el botón para intentar leer datos de la balanza directamente desde el navegador.
              </p>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleProbarBalanza(false)}
                disabled={probandoBalanza}
              >
                {probandoBalanza ? "Escuchando puerto..." : "Probar Balanza (Automático)"}
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() => handleProbarBalanza(true)}
                disabled={probandoBalanza}
                className="ml-2"
              >
                Seleccionar Nuevo Puerto
              </Button>

              {testBalanzaData && (
                <div className="mt-4 p-2 bg-gray-900 text-green-400 font-mono text-xs rounded overflow-auto max-h-40">
                  <pre>{testBalanzaData}</pre>
                </div>
              )}
            </div>

            <div className="p-4 border border-gray-200 bg-gray-50 rounded-md mt-4">
              <h3 className="font-semibold text-gray-800 mb-2">Drivers y Herramientas</h3>
              <p className="text-sm text-gray-600 mb-4">
                Si tiene problemas para conectar la balanza, descargue los drivers necesarios.
              </p>
              <a
                href="/Drivers_WIN.zip"
                download="Drivers_WIN.zip"
                className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
              >
                📥 Descargar Drivers (Windows)
              </a>
            </div>

            <FormField
              control={form.control}
              name="balanza_articulo_id"
              render={({ field }) => (
                <FormItem className="flex flex-col">
                  <FormLabel>Artículo para Balanza</FormLabel>
                  <Popover>
                    <PopoverTrigger asChild>
                      <FormControl>
                        <Button
                          variant="outline"
                          role="combobox"
                          className={cn(
                            "w-full justify-between",
                            !field.value && "text-muted-foreground"
                          )}
                        >
                          {field.value
                            ? articulos.find(
                              (articulo) => articulo.id === field.value
                            )?.nombre
                            : "Selecciona un artículo"}
                          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                        </Button>
                      </FormControl>
                    </PopoverTrigger>
                    <PopoverContent className="w-[400px] p-0">
                      <Command>
                        <CommandInput placeholder="Buscar artículo..." />
                        <CommandList>
                          <CommandEmpty>No se encontró el artículo.</CommandEmpty>
                          <CommandGroup>
                            {articulos.map((articulo) => (
                              <CommandItem
                                value={articulo.nombre}
                                key={articulo.id}
                                onSelect={() => {
                                  form.setValue("balanza_articulo_id", articulo.id, { shouldDirty: true });
                                }}
                              >
                                <Check
                                  className={cn(
                                    "mr-2 h-4 w-4",
                                    articulo.id === field.value
                                      ? "opacity-100"
                                      : "opacity-0"
                                  )}
                                />
                                {articulo.nombre}
                              </CommandItem>
                            ))}
                          </CommandGroup>
                        </CommandList>
                      </Command>
                    </PopoverContent>
                  </Popover>
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
                  <FormDescription>
                    {field.value === "producto"
                      ? "Se utilizará el precio definido en el catálogo del sistema multiplicado por el peso."
                      : "Se utilizará el precio total o unitario enviado directamente por la balanza."}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        )}

        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Guardando..." : "Guardar Cambios"}
        </Button>
      </form>
    </Form>
  );
}
