"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Barcode,
  Check,
  Layers,
  Package,
  Sparkles,
  Tag,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { ProductoFormData, ProductoModoEspecial, UnidadMedida } from "./api";
import { generarSugerenciasCodigoInterno } from "./codigoInternoSugerencias";

const UNIDADES: UnidadMedida[] = ["unidad", "gramos", "kilogramos", "litros", "mililitros"];

export const formVacio = (): ProductoFormData => ({
  codigo_interno: "",
  descripcion: "",
  precio_venta: "",
  precio_costo: "",
  categorias: "",
  stock: "",
  stock_minimo: "",
  barcodes: "",
  unidad: "unidad",
  cantidad_envase: "",
  ubicacion: "",
  tasa_iva: "0.21",
});

function tasaIvaAForm(tasa?: number | null): "0.21" | "0.105" {
  if (tasa == null) return "0.21";
  const n = tasa > 1 ? tasa / 100 : tasa;
  return Math.abs(n - 0.105) < 0.001 ? "0.105" : "0.21";
}

export function productoAForm(p: ProductoModoEspecial): ProductoFormData {
  return {
    codigo_interno: p.codigo_interno,
    descripcion: p.descripcion,
    precio_venta: String(p.precio_venta),
    precio_costo: p.precio_costo ? String(p.precio_costo) : "",
    categorias: p.categorias.join(", "),
    stock: String(p.stock_actual),
    stock_minimo: p.stock_minimo != null ? String(p.stock_minimo) : "",
    barcodes: p.barcodes.join(", "),
    unidad: (p.unidad as UnidadMedida) || "unidad",
    cantidad_envase: p.cantidad_envase != null ? String(p.cantidad_envase) : "",
    ubicacion: p.ubicacion || "",
    tasa_iva: tasaIvaAForm(p.tasa_iva),
  };
}

const PASOS = [
  { id: "identidad", titulo: "Producto", icon: Package, descripcion: "Nombre e identificador" },
  { id: "clasificacion", titulo: "Clasificación", icon: Layers, descripcion: "Categorías y unidad" },
  { id: "precios", titulo: "Precios", icon: Tag, descripcion: "Venta y costo" },
  { id: "stock", titulo: "Stock", icon: Sparkles, descripcion: "Cantidades e ubicación" },
  { id: "barcodes", titulo: "Códigos", icon: Barcode, descripcion: "Barras (opcional)" },
] as const;

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editando: ProductoModoEspecial | null;
  form: ProductoFormData;
  onFormChange: (form: ProductoFormData) => void;
  codigosExistentes: string[];
  guardando: boolean;
  onGuardar: () => void;
};

function formatMoneyPreview(value: string): string {
  const n = parseFloat(value);
  if (Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS" }).format(n);
}

export function ProductoWizardModal({
  open,
  onOpenChange,
  editando,
  form,
  onFormChange,
  codigosExistentes,
  guardando,
  onGuardar,
}: Props) {
  const [paso, setPaso] = useState(0);
  const [pasosCompletados, setPasosCompletados] = useState<Set<number>>(new Set());
  const [codigoManual, setCodigoManual] = useState(false);

  const sugerencias = useMemo(
    () =>
      editando
        ? []
        : generarSugerenciasCodigoInterno(form.descripcion, codigosExistentes, form.codigo_interno),
    [codigosExistentes, editando, form.codigo_interno, form.descripcion],
  );

  const resetWizard = useCallback(() => {
    setPaso(0);
    setPasosCompletados(new Set());
    setCodigoManual(false);
  }, []);

  useEffect(() => {
    if (!open) {
      resetWizard();
      return;
    }
    if (editando) {
      setPasosCompletados(new Set(PASOS.map((_, i) => i)));
      setCodigoManual(true);
    }
  }, [editando, open, resetWizard]);

  useEffect(() => {
    if (editando || codigoManual || !form.descripcion.trim() || sugerencias.length === 0) return;
    if (!form.codigo_interno.trim()) {
      onFormChange({ ...form, codigo_interno: sugerencias[0] });
    }
  }, [codigoManual, editando, form, onFormChange, sugerencias]);

  const validarPaso = (index: number): boolean => {
    switch (index) {
      case 0:
        if (!form.descripcion.trim()) {
          toast.error("Ingresá el nombre del producto.");
          return false;
        }
        if (!editando && !form.codigo_interno.trim()) {
          toast.error("Elegí o ingresá un código interno.");
          return false;
        }
        return true;
      case 1:
        if (!form.categorias.trim()) {
          toast.error("Indicá al menos una categoría.");
          return false;
        }
        return true;
      case 2:
        if (!form.precio_venta.trim() || Number.isNaN(parseFloat(form.precio_venta))) {
          toast.error("Ingresá un precio de venta válido.");
          return false;
        }
        return true;
      default:
        return true;
    }
  };

  const avanzar = () => {
    if (!validarPaso(paso)) return;
    setPasosCompletados((prev) => new Set(prev).add(paso));
    if (paso < PASOS.length - 1) {
      setPaso((p) => p + 1);
    }
  };

  const retroceder = () => {
    if (paso > 0) setPaso((p) => p - 1);
  };

  const irAPaso = (index: number) => {
    if (editando || index <= paso || pasosCompletados.has(index - 1)) {
      setPaso(index);
    }
  };

  const confirmar = () => {
    if (!validarPaso(paso)) return;
    for (let i = 0; i <= 2; i += 1) {
      if (!validarPaso(i)) {
        setPaso(i);
        return;
      }
    }
    onGuardar();
  };

  const pasoActual = PASOS[paso];
  const IconoPaso = pasoActual.icon;
  const esUltimoPaso = paso === PASOS.length - 1;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[92vh] w-[calc(100%-1.5rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-xl">
        <DialogHeader className="shrink-0 border-b bg-gradient-to-r from-amber-50 to-orange-50 px-6 py-4 pr-12">
          <DialogTitle className="text-amber-950">
            {editando ? "Editar producto" : "Nuevo producto"}
          </DialogTitle>
          <p className="text-sm text-amber-800/80">
            {editando
              ? "Modificá los datos por secciones."
              : "Completá el alta en pasos. El código se sugiere automáticamente."}
          </p>
        </DialogHeader>

        <div className="shrink-0 border-b bg-background px-4 py-4 sm:px-6">
          <ol className="flex items-center justify-between gap-1">
            {PASOS.map((p, index) => {
              const completado = pasosCompletados.has(index) || (editando && index < paso);
              const activo = index === paso;
              const Icon = p.icon;
              const clickeable = editando || index <= paso || pasosCompletados.has(index - 1);

              return (
                <li key={p.id} className="flex flex-1 items-center">
                  <button
                    type="button"
                    disabled={!clickeable}
                    onClick={() => irAPaso(index)}
                    className={cn(
                      "group flex flex-col items-center gap-1 transition-opacity",
                      clickeable ? "cursor-pointer" : "cursor-default opacity-60",
                    )}
                  >
                    <span
                      className={cn(
                        "flex size-9 items-center justify-center rounded-full border-2 text-xs font-semibold transition-colors",
                        activo && "border-amber-500 bg-amber-500 text-white shadow-md shadow-amber-200",
                        !activo && completado && "border-emerald-500 bg-emerald-50 text-emerald-700",
                        !activo && !completado && "border-muted-foreground/25 bg-muted/40 text-muted-foreground",
                      )}
                    >
                      {completado && !activo ? (
                        <Check className="size-4" />
                      ) : (
                        <Icon className="size-4" />
                      )}
                    </span>
                    <span
                      className={cn(
                        "hidden text-[10px] font-medium leading-tight sm:block",
                        activo ? "text-amber-900" : "text-muted-foreground",
                      )}
                    >
                      {p.titulo}
                    </span>
                  </button>
                  {index < PASOS.length - 1 && (
                    <div
                      className={cn(
                        "mx-1 h-0.5 flex-1 rounded-full transition-colors",
                        pasosCompletados.has(index) ? "bg-emerald-400" : "bg-muted",
                      )}
                    />
                  )}
                </li>
              );
            })}
          </ol>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          <div className="mb-4 flex items-start gap-3 rounded-lg border border-amber-200/80 bg-amber-50/60 p-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-800">
              <IconoPaso className="size-5" />
            </div>
            <div>
              <h3 className="font-semibold text-amber-950">{pasoActual.titulo}</h3>
              <p className="text-sm text-amber-900/70">{pasoActual.descripcion}</p>
            </div>
          </div>

          {paso === 0 && (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-200">
              <div className="space-y-2">
                <Label htmlFor="prod-descripcion">Nombre del producto *</Label>
                <Input
                  id="prod-descripcion"
                  placeholder="Ej: Yerba mate 500g"
                  value={form.descripcion}
                  autoFocus
                  onChange={(e) => onFormChange({ ...form, descripcion: e.target.value })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      avanzar();
                    }
                  }}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="prod-codigo">Código interno / SKU *</Label>
                {editando ? (
                  <Badge variant="secondary" className="font-mono text-sm px-3 py-1.5">
                    {form.codigo_interno}
                  </Badge>
                ) : (
                  <>
                    <Input
                      id="prod-codigo"
                      placeholder="Se sugiere al escribir el nombre"
                      value={form.codigo_interno}
                      className="font-mono"
                      onChange={(e) => {
                        setCodigoManual(true);
                        onFormChange({ ...form, codigo_interno: e.target.value.toUpperCase() });
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          avanzar();
                        }
                      }}
                    />
                    {sugerencias.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-xs text-muted-foreground">Sugerencias disponibles:</p>
                        <div className="flex flex-wrap gap-2">
                          {sugerencias.map((codigo) => (
                            <button
                              key={codigo}
                              type="button"
                              onClick={() => {
                                setCodigoManual(true);
                                onFormChange({ ...form, codigo_interno: codigo });
                              }}
                              className={cn(
                                "rounded-full border px-3 py-1 font-mono text-xs transition-colors",
                                form.codigo_interno === codigo
                                  ? "border-amber-500 bg-amber-100 text-amber-950"
                                  : "border-amber-200 bg-white text-amber-900 hover:bg-amber-50",
                              )}
                            >
                              {codigo}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          {paso === 1 && (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-200">
              <div className="space-y-2">
                <Label htmlFor="prod-categorias">Categorías (separadas por coma) *</Label>
                <Input
                  id="prod-categorias"
                  placeholder="Ej: Almacén, Bebidas"
                  value={form.categorias}
                  autoFocus
                  onChange={(e) => onFormChange({ ...form, categorias: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Unidad de medida</Label>
                  <Select
                    value={form.unidad}
                    onValueChange={(v) => onFormChange({ ...form, unidad: v as UnidadMedida })}
                  >
                    <SelectTrigger><SelectValue placeholder="Unidad" /></SelectTrigger>
                    <SelectContent>
                      {UNIDADES.map((u) => (
                        <SelectItem key={u} value={u}>{u}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="prod-envase">Cantidad envase</Label>
                  <Input
                    id="prod-envase"
                    placeholder="Ej: 500"
                    value={form.cantidad_envase}
                    onChange={(e) => onFormChange({ ...form, cantidad_envase: e.target.value })}
                  />
                </div>
              </div>
            </div>
          )}

          {paso === 2 && (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-200">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="prod-precio-venta">Precio venta *</Label>
                  <Input
                    id="prod-precio-venta"
                    type="number"
                    min="0"
                    step="any"
                    placeholder="0"
                    value={form.precio_venta}
                    autoFocus
                    onChange={(e) => onFormChange({ ...form, precio_venta: e.target.value })}
                  />
                  {form.precio_venta && (
                    <p className="text-xs text-emerald-700">{formatMoneyPreview(form.precio_venta)}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="prod-precio-costo">Costo</Label>
                  <Input
                    id="prod-precio-costo"
                    type="number"
                    min="0"
                    step="any"
                    placeholder="Opcional"
                    value={form.precio_costo}
                    onChange={(e) => onFormChange({ ...form, precio_costo: e.target.value })}
                  />
                  {form.precio_costo && (
                    <p className="text-xs text-muted-foreground">{formatMoneyPreview(form.precio_costo)}</p>
                  )}
                </div>
              </div>
              <div className="space-y-2">
                <Label>IVA al facturar</Label>
                <Select
                  value={form.tasa_iva}
                  onValueChange={(v) =>
                    onFormChange({ ...form, tasa_iva: v as "0.21" | "0.105" })
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Alícuota IVA" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0.21">21% (general)</SelectItem>
                    <SelectItem value="0.105">10,5% (carnes)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  El precio de venta es el final (con IVA). Esta alícuota solo cambia el desglose fiscal.
                </p>
              </div>
            </div>
          )}

          {paso === 3 && (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-200">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="prod-stock">Stock inicial</Label>
                  <Input
                    id="prod-stock"
                    type="number"
                    min="0"
                    step="any"
                    placeholder="0"
                    value={form.stock}
                    autoFocus
                    onChange={(e) => onFormChange({ ...form, stock: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="prod-stock-min">Stock mínimo</Label>
                  <Input
                    id="prod-stock-min"
                    type="number"
                    min="0"
                    step="any"
                    placeholder="Opcional"
                    value={form.stock_minimo}
                    onChange={(e) => onFormChange({ ...form, stock_minimo: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="prod-ubicacion">Ubicación en depósito</Label>
                <Input
                  id="prod-ubicacion"
                  placeholder="Ej: Estante A3"
                  value={form.ubicacion}
                  onChange={(e) => onFormChange({ ...form, ubicacion: e.target.value })}
                />
              </div>
            </div>
          )}

          {paso === 4 && (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-200">
              <div className="space-y-2">
                <Label htmlFor="prod-barcodes">Códigos de barra</Label>
                <Input
                  id="prod-barcodes"
                  placeholder="Separados por coma (opcional)"
                  value={form.barcodes}
                  autoFocus
                  onChange={(e) => onFormChange({ ...form, barcodes: e.target.value })}
                />
              </div>

              <div className="rounded-lg border bg-muted/30 p-4 text-sm space-y-2">
                <p className="font-medium text-foreground">Resumen</p>
                <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-muted-foreground">
                  <dt>Código</dt>
                  <dd className="font-mono text-foreground">{form.codigo_interno || "—"}</dd>
                  <dt>Producto</dt>
                  <dd className="text-foreground">{form.descripcion || "—"}</dd>
                  <dt>Categorías</dt>
                  <dd className="text-foreground">{form.categorias || "—"}</dd>
                  <dt>Precio</dt>
                  <dd className="text-foreground">{formatMoneyPreview(form.precio_venta)}</dd>
                  <dt>IVA</dt>
                  <dd className="text-foreground">
                    {form.tasa_iva === "0.105" ? "10,5% (carnes)" : "21%"}
                  </dd>
                  <dt>Stock</dt>
                  <dd className="text-foreground">{form.stock || "0"} {form.unidad}</dd>
                </dl>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="shrink-0 border-t bg-background px-6 py-4 sm:justify-between">
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              className="border-amber-300 text-amber-950 hover:bg-amber-50"
              disabled={paso === 0}
              onClick={retroceder}
            >
              <ArrowLeft className="size-4" />
              Anterior
            </Button>
            {esUltimoPaso ? (
              <Button type="button" onClick={confirmar} disabled={guardando}>
                {guardando ? "Guardando..." : editando ? "Guardar cambios" : "Crear producto"}
              </Button>
            ) : (
              <Button type="button" onClick={avanzar}>
                Siguiente
                <ArrowRight className="size-4" />
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
