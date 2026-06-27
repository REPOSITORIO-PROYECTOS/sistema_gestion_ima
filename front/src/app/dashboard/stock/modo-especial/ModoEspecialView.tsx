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
  crearTransferenciaStock,
  exportarProductosModoEspecial,
  EmpresaTransferencia,
  fetchEmpresasTransferencia,
  fetchProductosModoEspecial,
  fetchTransferenciasPendientes,
  importarProductosModoEspecial,
  ingresarStockModoEspecial,
  ProductoFormData,
  ProductoModoEspecial,
  recibirTransferenciaStock,
  subaPreciosModoEspecial,
  TransferenciaStock,
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

interface IngresoLinea {
  id: string;
  codigo_interno: string;
  cantidad: string;
  precio_venta: string;
  precio_costo: string;
}

interface TransferenciaLinea {
  id: string;
  codigo_interno: string;
  cantidad: string;
  precio_unitario: string;
}

const nuevaLineaIngreso = (): IngresoLinea => ({
  id: crypto.randomUUID(),
  codigo_interno: "",
  cantidad: "",
  precio_venta: "",
  precio_costo: "",
});

const nuevaLineaTransferencia = (): TransferenciaLinea => ({
  id: crypto.randomUUID(),
  codigo_interno: "",
  cantidad: "",
  precio_unitario: "",
});

export function ModoEspecialView() {
  const token = useAuthStore((s) => s.token);
  const [productos, setProductos] = useState<ProductoModoEspecial[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState("");
  const [modalProducto, setModalProducto] = useState(false);
  const [modalIngreso, setModalIngreso] = useState(false);
  const [modalSuba, setModalSuba] = useState(false);
  const [modalTransferencia, setModalTransferencia] = useState(false);
  const [modalRecepcion, setModalRecepcion] = useState(false);
  const [editando, setEditando] = useState<ProductoModoEspecial | null>(null);
  const [form, setForm] = useState<ProductoFormData>(formVacio());
  const [lineasIngreso, setLineasIngreso] = useState<IngresoLinea[]>([nuevaLineaIngreso()]);
  const [ingresoObs, setIngresoObs] = useState("");
  const [empresasTransferencia, setEmpresasTransferencia] = useState<EmpresaTransferencia[]>([]);
  const [empresaDestinoId, setEmpresaDestinoId] = useState("");
  const [lineasTransferencia, setLineasTransferencia] = useState<TransferenciaLinea[]>([nuevaLineaTransferencia()]);
  const [transferenciaObs, setTransferenciaObs] = useState("");
  const [pendientes, setPendientes] = useState<TransferenciaStock[]>([]);
  const [transferenciaSeleccionada, setTransferenciaSeleccionada] = useState<TransferenciaStock | null>(null);
  const [cantidadesRecepcion, setCantidadesRecepcion] = useState<Record<number, string>>({});
  const [aplicarPreciosRecepcion, setAplicarPreciosRecepcion] = useState(true);
  const [porcentajeSuba, setPorcentajeSuba] = useState("");
  const [categoriaSuba, setCategoriaSuba] = useState("");
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [data, pend, empresas] = await Promise.all([
        fetchProductosModoEspecial(token),
        fetchTransferenciasPendientes(token).catch(() => [] as TransferenciaStock[]),
        fetchEmpresasTransferencia(token).catch(() => [] as EmpresaTransferencia[]),
      ]);
      setProductos(data);
      setPendientes(pend);
      setEmpresasTransferencia(empresas);
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
    if (!token) return;
    const items = lineasIngreso
      .map((linea) => {
        const codigo = linea.codigo_interno.trim();
        const cantidad = parseFloat(linea.cantidad);
        if (!codigo || !cantidad || cantidad <= 0) return null;
        const item: {
          codigo_interno: string;
          cantidad: number;
          observacion?: string;
          precio_venta?: number;
          precio_costo?: number;
        } = { codigo_interno: codigo, cantidad };
        if (ingresoObs.trim()) item.observacion = ingresoObs.trim();
        if (linea.precio_venta.trim()) item.precio_venta = parseFloat(linea.precio_venta);
        if (linea.precio_costo.trim()) item.precio_costo = parseFloat(linea.precio_costo);
        return item;
      })
      .filter((item): item is NonNullable<typeof item> => item !== null);

    if (items.length === 0) {
      toast.error("Agregá al menos una línea con código y cantidad.");
      return;
    }
    setGuardando(true);
    try {
      const res = await ingresarStockModoEspecial(token, items);
      toast.success(`Ingreso registrado: ${res.total} artículo(s).`);
      setModalIngreso(false);
      setLineasIngreso([nuevaLineaIngreso()]);
      setIngresoObs("");
      await cargar();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error en ingreso");
    } finally {
      setGuardando(false);
    }
  };

  const abrirTransferencia = () => {
    setLineasTransferencia([nuevaLineaTransferencia()]);
    setTransferenciaObs("");
    setEmpresaDestinoId(empresasTransferencia[0] ? String(empresasTransferencia[0].id) : "");
    setModalTransferencia(true);
  };

  const enviarTransferencia = async () => {
    if (!token || !empresaDestinoId) {
      toast.error("Seleccioná la empresa destino.");
      return;
    }
    const items = lineasTransferencia
      .map((linea) => {
        const codigo = linea.codigo_interno.trim();
        const cantidad = parseFloat(linea.cantidad);
        if (!codigo || !cantidad || cantidad <= 0) return null;
        const item: { codigo_interno: string; cantidad: number; precio_unitario?: number } = {
          codigo_interno: codigo,
          cantidad,
        };
        if (linea.precio_unitario.trim()) item.precio_unitario = parseFloat(linea.precio_unitario);
        return item;
      })
      .filter((item): item is NonNullable<typeof item> => item !== null);

    if (items.length === 0) {
      toast.error("Agregá al menos un producto con cantidad.");
      return;
    }
    setGuardando(true);
    try {
      await crearTransferenciaStock(token, {
        id_empresa_destino: parseInt(empresaDestinoId, 10),
        observacion: transferenciaObs.trim() || undefined,
        items,
      });
      toast.success("Transferencia enviada. El stock fue descontado.");
      setModalTransferencia(false);
      await cargar();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al enviar transferencia");
    } finally {
      setGuardando(false);
    }
  };

  const abrirRecepcion = (transferencia: TransferenciaStock) => {
    setTransferenciaSeleccionada(transferencia);
    const cantidades: Record<number, string> = {};
    transferencia.detalles.forEach((d) => {
      cantidades[d.id] = String(d.cantidad);
    });
    setCantidadesRecepcion(cantidades);
    setAplicarPreciosRecepcion(true);
    setModalRecepcion(true);
  };

  const confirmarRecepcion = async () => {
    if (!token || !transferenciaSeleccionada) return;
    const items = transferenciaSeleccionada.detalles.map((d) => {
      const raw = cantidadesRecepcion[d.id];
      const cantidad = raw ? parseFloat(raw) : d.cantidad;
      return {
        id_detalle: d.id,
        cantidad_recibida: cantidad > 0 ? cantidad : undefined,
      };
    });
    setGuardando(true);
    try {
      await recibirTransferenciaStock(token, transferenciaSeleccionada.id, {
        aplicar_precios: aplicarPreciosRecepcion,
        items,
      });
      toast.success("Transferencia recibida e ingresada al stock.");
      setModalRecepcion(false);
      setTransferenciaSeleccionada(null);
      await cargar();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error al recibir transferencia");
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
          <Button variant="outline" onClick={() => { setLineasIngreso([nuevaLineaIngreso()]); setModalIngreso(true); }}>
            Ingreso de stock
          </Button>
          {empresasTransferencia.length > 0 && (
            <>
              <Button variant="outline" onClick={abrirTransferencia}>Enviar a sucursal</Button>
              <Button variant="outline" onClick={() => setModalRecepcion(true)}>
                Recepción{pendientes.length > 0 ? ` (${pendientes.length})` : ""}
              </Button>
            </>
          )}
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
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Ingreso masivo de stock</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Cargá varios productos a la vez. Los precios son opcionales; si los dejás en blanco no se modifican.
          </p>
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Código *</TableHead>
                  <TableHead>Cantidad *</TableHead>
                  <TableHead>Precio venta</TableHead>
                  <TableHead>Precio costo</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {lineasIngreso.map((linea) => (
                  <TableRow key={linea.id}>
                    <TableCell>
                      <Input
                        placeholder="SKU"
                        value={linea.codigo_interno}
                        onChange={(e) => setLineasIngreso((prev) =>
                          prev.map((l) => l.id === linea.id ? { ...l, codigo_interno: e.target.value } : l)
                        )}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min="0"
                        step="any"
                        placeholder="0"
                        value={linea.cantidad}
                        onChange={(e) => setLineasIngreso((prev) =>
                          prev.map((l) => l.id === linea.id ? { ...l, cantidad: e.target.value } : l)
                        )}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min="0"
                        step="any"
                        placeholder="Opcional"
                        value={linea.precio_venta}
                        onChange={(e) => setLineasIngreso((prev) =>
                          prev.map((l) => l.id === linea.id ? { ...l, precio_venta: e.target.value } : l)
                        )}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        type="number"
                        min="0"
                        step="any"
                        placeholder="Opcional"
                        value={linea.precio_costo}
                        onChange={(e) => setLineasIngreso((prev) =>
                          prev.map((l) => l.id === linea.id ? { ...l, precio_costo: e.target.value } : l)
                        )}
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={lineasIngreso.length <= 1}
                        onClick={() => setLineasIngreso((prev) => prev.filter((l) => l.id !== linea.id))}
                      >
                        Quitar
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <Button variant="outline" size="sm" onClick={() => setLineasIngreso((prev) => [...prev, nuevaLineaIngreso()])}>
            + Agregar línea
          </Button>
          <Input placeholder="Observación general (opcional)" value={ingresoObs} onChange={(e) => setIngresoObs(e.target.value)} />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setModalIngreso(false)}>Cancelar</Button>
            <Button onClick={registrarIngreso} disabled={guardando}>Registrar ingreso</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={modalTransferencia} onOpenChange={setModalTransferencia}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Enviar stock a otra sucursal</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3">
            <Select value={empresaDestinoId} onValueChange={setEmpresaDestinoId}>
              <SelectTrigger><SelectValue placeholder="Empresa destino" /></SelectTrigger>
              <SelectContent>
                {empresasTransferencia.map((e) => (
                  <SelectItem key={e.id} value={String(e.id)}>{e.nombre}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Al enviar se descuenta el stock de esta sucursal. El precio unitario es opcional (costo de transferencia).
            </p>
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Código *</TableHead>
                    <TableHead>Cantidad *</TableHead>
                    <TableHead>Precio unit.</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {lineasTransferencia.map((linea) => (
                    <TableRow key={linea.id}>
                      <TableCell>
                        <Input
                          placeholder="SKU"
                          value={linea.codigo_interno}
                          onChange={(e) => setLineasTransferencia((prev) =>
                            prev.map((l) => l.id === linea.id ? { ...l, codigo_interno: e.target.value } : l)
                          )}
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="any"
                          value={linea.cantidad}
                          onChange={(e) => setLineasTransferencia((prev) =>
                            prev.map((l) => l.id === linea.id ? { ...l, cantidad: e.target.value } : l)
                          )}
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          type="number"
                          min="0"
                          step="any"
                          placeholder="Opcional"
                          value={linea.precio_unitario}
                          onChange={(e) => setLineasTransferencia((prev) =>
                            prev.map((l) => l.id === linea.id ? { ...l, precio_unitario: e.target.value } : l)
                          )}
                        />
                      </TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={lineasTransferencia.length <= 1}
                          onClick={() => setLineasTransferencia((prev) => prev.filter((l) => l.id !== linea.id))}
                        >
                          Quitar
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <Button variant="outline" size="sm" onClick={() => setLineasTransferencia((prev) => [...prev, nuevaLineaTransferencia()])}>
              + Agregar producto
            </Button>
            <Input placeholder="Observación (opcional)" value={transferenciaObs} onChange={(e) => setTransferenciaObs(e.target.value)} />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setModalTransferencia(false)}>Cancelar</Button>
            <Button onClick={enviarTransferencia} disabled={guardando}>Enviar transferencia</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={modalRecepcion} onOpenChange={(open) => {
        setModalRecepcion(open);
        if (!open) setTransferenciaSeleccionada(null);
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {transferenciaSeleccionada
                ? `Recibir transferencia #${transferenciaSeleccionada.id}`
                : "Recepción de transferencias"}
            </DialogTitle>
          </DialogHeader>
          {!transferenciaSeleccionada ? (
            <div className="space-y-3">
              {pendientes.length === 0 ? (
                <p className="text-muted-foreground text-sm py-4 text-center">No hay transferencias pendientes.</p>
              ) : (
                pendientes.map((t) => (
                  <div key={t.id} className="flex items-center justify-between rounded-lg border p-3 gap-3">
                    <div>
                      <p className="font-medium">#{t.id} — desde {t.nombre_empresa_origen}</p>
                      <p className="text-sm text-muted-foreground">
                        {t.detalles.length} producto(s) · {new Date(t.creada_en).toLocaleString("es-AR")}
                      </p>
                      {t.observacion && <p className="text-sm italic">{t.observacion}</p>}
                    </div>
                    <Button size="sm" onClick={() => abrirRecepcion(t)}>Controlar e ingresar</Button>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Origen: <strong>{transferenciaSeleccionada.nombre_empresa_origen}</strong>.
                Verificá las cantidades recibidas antes de confirmar.
              </p>
              <div className="rounded-md border overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Código</TableHead>
                      <TableHead>Producto</TableHead>
                      <TableHead>Enviado</TableHead>
                      <TableHead>Recibido</TableHead>
                      <TableHead>Precio unit.</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {transferenciaSeleccionada.detalles.map((d) => (
                      <TableRow key={d.id}>
                        <TableCell className="font-mono text-sm">{d.codigo_interno}</TableCell>
                        <TableCell>{d.descripcion}</TableCell>
                        <TableCell>{d.cantidad}</TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min="0"
                            max={d.cantidad}
                            step="any"
                            className="w-24"
                            value={cantidadesRecepcion[d.id] ?? String(d.cantidad)}
                            onChange={(e) => setCantidadesRecepcion((prev) => ({ ...prev, [d.id]: e.target.value }))}
                          />
                        </TableCell>
                        <TableCell>
                          {d.precio_unitario != null ? formatMoney(d.precio_unitario) : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={aplicarPreciosRecepcion}
                  onChange={(e) => setAplicarPreciosRecepcion(e.target.checked)}
                />
                Aplicar precio unitario como costo del producto
              </label>
              <DialogFooter>
                <Button variant="ghost" onClick={() => setTransferenciaSeleccionada(null)}>Volver</Button>
                <Button onClick={confirmarRecepcion} disabled={guardando}>Confirmar ingreso</Button>
              </DialogFooter>
            </div>
          )}
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
