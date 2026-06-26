"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  actualizarProductoModoEspecial,
  crearProductoModoEspecial,
  exportarProductosModoEspecial,
  fetchProductosModoEspecial,
  importarProductosModoEspecial,
  ingresarStockModoEspecial,
  ProductoFormData,
  ProductoModoEspecial,
  subaPreciosModoEspecial,
  UnidadMedida,
} from "./api";

const UNIDADES: UnidadMedida[] = ["unidad", "gramos", "kilogramos", "litros", "mililitros"];

const formVacio = (): ProductoFormData => ({
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
});

function productoAForm(p: ProductoModoEspecial): ProductoFormData {
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
  };
}

function formatMoney(value: number) {
  return new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS" }).format(value);
}

export function ModoEspecialView() {
  const token = useAuthStore((s) => s.token);
  const [productos, setProductos] = useState<ProductoModoEspecial[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState("");
  const [modalProducto, setModalProducto] = useState(false);
  const [modalIngreso, setModalIngreso] = useState(false);
  const [modalSuba, setModalSuba] = useState(false);
  const [editando, setEditando] = useState<ProductoModoEspecial | null>(null);
  const [form, setForm] = useState<ProductoFormData>(formVacio());
  const [ingresoCodigo, setIngresoCodigo] = useState("");
  const [ingresoCantidad, setIngresoCantidad] = useState("");
  const [ingresoObs, setIngresoObs] = useState("");
  const [porcentajeSuba, setPorcentajeSuba] = useState("");
  const [categoriaSuba, setCategoriaSuba] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await fetchProductosModoEspecial(token);
      setProductos(data);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al cargar productos");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const abrirCrear = () => {
    setEditando(null);
    setForm(formVacio());
    setModalProducto(true);
  };

  const abrirEditar = (p: ProductoModoEspecial) => {
    setEditando(p);
    setForm(productoAForm(p));
    setModalProducto(true);
  };

  const guardarProducto = async () => {
    if (!token) return;
    if (!form.codigo_interno || !form.descripcion || !form.precio_venta || !form.categorias) {
      toast.error("Completa código, nombre, precio y al menos una categoría.");
      return;
    }
    setGuardando(true);
    try {
      if (editando) {
        await actualizarProductoModoEspecial(token, editando.codigo_interno, form);
        toast.success("Producto actualizado.");
      } else {
        await crearProductoModoEspecial(token, form);
        toast.success("Producto creado.");
      }
      setModalProducto(false);
      await cargar();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setGuardando(false);
    }
  };

  const registrarIngreso = async () => {
    if (!token || !ingresoCodigo || !ingresoCantidad) {
      toast.error("Indica código y cantidad.");
      return;
    }
    setGuardando(true);
    try {
      await ingresarStockModoEspecial(token, [{
        codigo_interno: ingresoCodigo.trim(),
        cantidad: parseFloat(ingresoCantidad),
        observacion: ingresoObs.trim() || undefined,
      }]);
      toast.success("Ingreso de stock registrado.");
      setModalIngreso(false);
      setIngresoCodigo("");
      setIngresoCantidad("");
      setIngresoObs("");
      await cargar();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error en ingreso");
    } finally {
      setGuardando(false);
    }
  };

  const aplicarSuba = async () => {
    if (!token) return;
    if (!porcentajeSuba && !categoriaSuba) {
      toast.error("Indica un porcentaje general o una categoría.");
      return;
    }
    setGuardando(true);
    try {
      const res = await subaPreciosModoEspecial(token, {
        porcentaje_general: porcentajeSuba ? parseFloat(porcentajeSuba) : undefined,
        categoria: categoriaSuba.trim() || undefined,
      });
      toast.success(`Suba aplicada a ${res.actualizados} producto(s).`);
      setModalSuba(false);
      setPorcentajeSuba("");
      setCategoriaSuba("");
      await cargar();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error en suba de precios");
    } finally {
      setGuardando(false);
    }
  };

  const handleExportar = async () => {
    if (!token) return;
    try {
      const blob = await exportarProductosModoEspecial(token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "productos_modo_especial.csv";
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Exportación completada.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al exportar");
    }
  };

  const handleImportar = async (file: File) => {
    if (!token) return;
    setGuardando(true);
    try {
      const res = await importarProductosModoEspecial(token, file);
      toast.success(`Importación: ${res.creados} creados, ${res.actualizados} actualizados.`);
      if (res.errores > 0) {
        const detalle = (res.detalle_errores || []).slice(0, 5).join(" | ");
        toast.warning(
          `${res.errores} fila(s) con error.${detalle ? ` ${detalle}` : ""}`,
          { duration: 12000 },
        );
      }
      await cargar();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al importar");
    } finally {
      setGuardando(false);
    }
  };

  const filtrados = productos.filter((p) => {
    const t = filtro.toLowerCase();
    return (
      p.descripcion.toLowerCase().includes(t) ||
      p.codigo_interno.toLowerCase().includes(t) ||
      p.barcodes.some((b) => b.toLowerCase().includes(t)) ||
      p.categorias.some((c) => c.toLowerCase().includes(t))
    );
  });

  if (loading) {
    return <p className="text-center py-10">Cargando catálogo modo especial...</p>;
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900 text-sm">
        <strong>Modo Especial activo.</strong> Este negocio no sincroniza con Google Sheets.
        Gestioná el catálogo manualmente desde aquí.
      </div>

      <div className="flex flex-col lg:flex-row gap-3 justify-between items-stretch lg:items-center">
        <Input
          placeholder="Buscar por nombre, código, barcode o categoría"
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          className="lg:max-w-sm"
        />
        <div className="flex flex-wrap gap-2">
          <Button onClick={abrirCrear}>Agregar producto</Button>
          <Button variant="outline" onClick={() => setModalIngreso(true)}>Ingreso de stock</Button>
          <Button variant="outline" onClick={() => setModalSuba(true)}>Suba de precios</Button>
          <Button variant="outline" onClick={handleExportar}>Exportar CSV</Button>
          <label className="inline-flex">
            <input
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleImportar(file);
                e.target.value = "";
              }}
            />
            <Button variant="outline" asChild>
              <span>Importar CSV</span>
            </Button>
          </label>
        </div>
      </div>

      <div className="rounded-md border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Código</TableHead>
              <TableHead>Producto</TableHead>
              <TableHead>Categorías</TableHead>
              <TableHead>Precio</TableHead>
              <TableHead>Stock</TableHead>
              <TableHead>Unidad</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtrados.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center h-24 text-muted-foreground">
                  No hay productos. Usá &quot;Agregar producto&quot; o importá un CSV.
                </TableCell>
              </TableRow>
            ) : (
              filtrados.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-mono text-sm">{p.codigo_interno}</TableCell>
                  <TableCell>{p.descripcion}</TableCell>
                  <TableCell>{p.categorias.join(", ") || "—"}</TableCell>
                  <TableCell>{formatMoney(p.precio_venta)}</TableCell>
                  <TableCell>
                    {p.stock_actual}
                    {p.stock_minimo != null && p.stock_actual < p.stock_minimo && (
                      <span className="ml-2 text-xs text-red-600 font-semibold">Bajo stock</span>
                    )}
                  </TableCell>
                  <TableCell>{p.unidad}</TableCell>
                  <TableCell className="text-right">
                    <Button size="sm" variant="ghost" onClick={() => abrirEditar(p)}>Editar</Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog open={modalProducto} onOpenChange={setModalProducto}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editando ? "Editar producto" : "Agregar producto"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 py-2">
            <Input
              placeholder="Código / SKU *"
              value={form.codigo_interno}
              disabled={Boolean(editando)}
              onChange={(e) => setForm({ ...form, codigo_interno: e.target.value })}
            />
            <Input
              placeholder="Nombre *"
              value={form.descripcion}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
            />
            <Input
              placeholder="Categorías (separadas por coma) *"
              value={form.categorias}
              onChange={(e) => setForm({ ...form, categorias: e.target.value })}
            />
            <Select value={form.unidad} onValueChange={(v) => setForm({ ...form, unidad: v as UnidadMedida })}>
              <SelectTrigger><SelectValue placeholder="Unidad" /></SelectTrigger>
              <SelectContent>
                {UNIDADES.map((u) => (
                  <SelectItem key={u} value={u}>{u}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="Precio venta *" value={form.precio_venta} onChange={(e) => setForm({ ...form, precio_venta: e.target.value })} />
              <Input placeholder="Costo" value={form.precio_costo} onChange={(e) => setForm({ ...form, precio_costo: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="Stock" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} />
              <Input placeholder="Stock mínimo" value={form.stock_minimo} onChange={(e) => setForm({ ...form, stock_minimo: e.target.value })} />
            </div>
            <Input placeholder="Cantidad envase (ej. 500)" value={form.cantidad_envase} onChange={(e) => setForm({ ...form, cantidad_envase: e.target.value })} />
            <Input placeholder="Códigos de barra (separados por coma)" value={form.barcodes} onChange={(e) => setForm({ ...form, barcodes: e.target.value })} />
            <Input placeholder="Ubicación" value={form.ubicacion} onChange={(e) => setForm({ ...form, ubicacion: e.target.value })} />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setModalProducto(false)}>Cancelar</Button>
            <Button onClick={guardarProducto} disabled={guardando}>
              {guardando ? "Guardando..." : "Guardar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={modalIngreso} onOpenChange={setModalIngreso}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ingreso de artículos al stock</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 py-2">
            <Input placeholder="Código interno *" value={ingresoCodigo} onChange={(e) => setIngresoCodigo(e.target.value)} />
            <Input placeholder="Cantidad *" type="number" min="0" step="any" value={ingresoCantidad} onChange={(e) => setIngresoCantidad(e.target.value)} />
            <Input placeholder="Observación (opcional)" value={ingresoObs} onChange={(e) => setIngresoObs(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setModalIngreso(false)}>Cancelar</Button>
            <Button onClick={registrarIngreso} disabled={guardando}>Registrar ingreso</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={modalSuba} onOpenChange={setModalSuba}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Suba de precios</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 py-2">
            <Input placeholder="% general (ej. 10)" value={porcentajeSuba} onChange={(e) => setPorcentajeSuba(e.target.value)} />
            <Input placeholder="O filtrar por categoría exacta" value={categoriaSuba} onChange={(e) => setCategoriaSuba(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setModalSuba(false)}>Cancelar</Button>
            <Button onClick={aplicarSuba} disabled={guardando}>Aplicar suba</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
