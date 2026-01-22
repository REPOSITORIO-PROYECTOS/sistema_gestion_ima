import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Loader2, Plus, X, Receipt, ChefHat, FileText } from 'lucide-react';
import { useMesasStore } from '@/lib/mesasStore';
import { useAuthStore } from '@/lib/authStore';
import { api } from '@/lib/api-client';
import { API_CONFIG } from '@/lib/api-config';
import type { ConsumoMesa, Articulo, TicketResponse } from '@/lib/types/mesas';
import { toast } from 'sonner';
import { routeToDepartments } from '@/lib/ticketRoutingService';

interface ConsumoModalProps {
  isOpen: boolean;
  onClose: () => void;
  consumo: ConsumoMesa | null;
  onTicketGenerated: (ticket: TicketResponse) => void;
}

export const ConsumoModal: React.FC<ConsumoModalProps> = ({ isOpen, onClose, consumo, onTicketGenerated }) => {
  const { addDetalleConsumo, cerrarConsumo, facturarConsumo, generarTicket, error, fetchConsumos } = useMesasStore();
  const { usuario } = useAuthStore();
  const [articulos, setArticulos] = useState<Articulo[]>([]);
  const [isLoadingArticulos, setIsLoadingArticulos] = useState(false);
  const [hasFetchedArticulos, setHasFetchedArticulos] = useState(false);
  const [selectedArticuloId, setSelectedArticuloId] = useState<string>('');
  const [cantidad, setCantidad] = useState<number>(1);
  const [observacion, setObservacion] = useState<string>('');
  const [porcentajePropina, setPorcentajePropina] = useState<number>(10);
  const [metodoPago, setMetodoPago] = useState<string>('Efectivo');
  const [cobrarPropina, setCobrarPropina] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState(false);
  const [isCheckoutMode, setIsCheckoutMode] = useState(false);

  // Estado local para carrito de pedidos antes de enviar
  const [localItems, setLocalItems] = useState<Array<{
    id_articulo: number;
    cantidad: number;
    observacion?: string;
    articulo: Articulo; // Para mostrar detalles
  }>>([]);

  const fetchArticulos = React.useCallback(async () => {
    if (!usuario?.id_empresa) {
      toast.error('ID de empresa no disponible para cargar artículos.');
      return;
    }
    setIsLoadingArticulos(true);
    try {
      const response = await api.articulos.getAll(usuario.id_empresa);
      if (response.success && Array.isArray(response.data)) {
        setArticulos(response.data);
        setHasFetchedArticulos(true);
      } else {
        toast.error(response.error || 'Error al cargar artículos');
      }
    } catch (err) {
      console.error("Error fetching articulos:", err);
      toast.error("Error al cargar artículos.");
    } finally {
      setIsLoadingArticulos(false);
    }
  }, [usuario?.id_empresa]);

  useEffect(() => {
    if (isOpen && usuario?.id_empresa && !hasFetchedArticulos) {
      fetchArticulos();
    }
  }, [isOpen, usuario?.id_empresa, fetchArticulos, hasFetchedArticulos]);
  
  useEffect(() => {
    if (!isOpen) return;
    let lastVersion = parseInt(localStorage.getItem("catalogo_version") || "0", 10);
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}/articulos/version`, {
          headers: { Authorization: `Bearer ${useAuthStore.getState().token || ''}` }
        });
        if (!res.ok) return;
        const data = await res.json() as { version?: number };
        const v = typeof data.version === "number" ? data.version : 0;
        if (v > lastVersion) {
          await fetchArticulos();
          lastVersion = v;
          localStorage.setItem("catalogo_version", String(v));
          toast.success("Catálogo de cocina actualizado");
        }
      } catch {}
    }, 5000);
    return () => clearInterval(interval);
  }, [isOpen, fetchArticulos]);

  const handleAddDetalle = async () => {
    if (!consumo || !selectedArticuloId || cantidad <= 0) {
      toast.error('Selecciona un artículo y una cantidad válida.');
      return;
    }

    const articulo = articulos.find(a => a.id === parseInt(selectedArticuloId, 10));
    if (!articulo) {
      toast.error("Artículo no encontrado.");
      return;
    }
    const latestRes = await api.articulos.getById(articulo.id);
    if (!latestRes.success || !latestRes.data) {
      toast.error(latestRes.error || "No se pudo verificar el artículo.");
      return;
    }
    const latest = latestRes.data as Articulo;
    if (latest.stock_actual < cantidad) {
      toast.error(`Stock insuficiente: disponible ${latest.stock_actual}, solicitado ${cantidad}.`);
      return;
    }

    // Agregar a la lista local (Carrito)
    setLocalItems(prev => [...prev, {
      id_articulo: parseInt(selectedArticuloId),
      cantidad,
      observacion: observacion || undefined,
      articulo: latest
    }]);

    toast.success('Agregado al pedido (Pendiente de envío).');
    setSelectedArticuloId('');
    setCantidad(1);
    setObservacion('');
  };

  const handleEnviarPedido = async () => {
    if (localItems.length === 0) return;

    setSubmitting(true);
    let errorCount = 0;

    // Enviar cada item
    for (const item of localItems) {
      const result = await addDetalleConsumo(consumo!.id, {
        id_articulo: item.id_articulo,
        cantidad: item.cantidad,
        precio_unitario: item.articulo.precio_venta,
        descuento_aplicado: 0,
        observacion: item.observacion
      });
      if (!result.ok) errorCount++;
    }

    setSubmitting(false);

    if (errorCount === 0) {
      toast.success("Pedido enviado a cocina correctamente");
      setLocalItems([]);
      fetchConsumos();
    } else {
      toast.error(`Se enviaron algunos items, pero ${errorCount} fallaron.`);
      // Opcional: mantener los fallidos en localItems? Por ahora limpiamos todo o refrescamos
      fetchConsumos();
      setLocalItems([]);
    }
  };

  const handleCerrarConsumo = async () => {
    if (!consumo) return;
    if (confirm(`¿Estás seguro de cerrar el consumo con ${porcentajePropina}% de propina?`)) {
      setSubmitting(true);
      const success = await cerrarConsumo(consumo.id, porcentajePropina);
      setSubmitting(false);
      if (success) {
        toast.success('Consumo cerrado exitosamente.');
        onClose();
      } else {
        toast.error(error || 'Error al cerrar consumo.');
      }
    }
  };

  const handleFacturarConsumo = async () => {
    if (!consumo) return;
    if (confirm('¿Estás seguro de que quieres facturar este consumo?')) {
      setSubmitting(true);
      const success = await facturarConsumo(consumo.id, metodoPago, cobrarPropina);
      setSubmitting(false);
      if (success) {
        // Imprimir Ticket al facturar
        const ticket = await generarTicket({ id_consumo_mesa: consumo.id, formato: 'ticket' });
        if (ticket) {
          const html = buildTicketHtml("TICKET DE VENTA", ticket);
          printHtml(html);
        }
        toast.success('Consumo facturado exitosamente.');
        onClose();
      } else {
        toast.error(error || 'Error al facturar consumo.');
      }
    }
  };

  

  const handleCheckout = async () => {
    if (!consumo) return;
    const totalConPropina = totalConsumo * (1 + porcentajePropina / 100);

    if (confirm(`¿Confirmar cobro total de $${totalConPropina.toFixed(2)}?`)) {
      setSubmitting(true);
      // 1. Cerrar Consumo (Calcula totales y propina)
      const closed = await cerrarConsumo(consumo.id, porcentajePropina);
      if (!closed) {
        setSubmitting(false);
        toast.error(error || 'Error al cerrar consumo.');
        return;
      }

      // 2. Facturar Consumo (Genera venta y movimiento de caja)
      // Nota: facturarConsumo usa el estado actualizado en el store, pero como acabamos de llamar a cerrarConsumo
      // y este actualiza el store, deberíamos estar bien. Sin embargo, para mayor seguridad,
      // confiamos en que cerrarConsumo devolvió true.
      const billed = await facturarConsumo(consumo.id, metodoPago, cobrarPropina);
      setSubmitting(false);

      if (billed) {
        toast.success('Cobro registrado y mesa liberada.');
        onClose();
      } else {
        toast.error(error || 'Error al facturar consumo.');
      }
    }
  };

  const totalConsumo = (consumo?.detalles?.reduce((sum, detalle) => sum + (detalle.cantidad * detalle.precio_unitario), 0) || 0) +
    (localItems.reduce((sum, item) => sum + (item.cantidad * item.articulo.precio_venta), 0));

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="w-full max-w-[95vw] sm:max-w-[800px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Consumo de Mesa {consumo?.mesa?.numero}</DialogTitle>
          <DialogDescription>
            Detalles del consumo actual. Total: ${totalConsumo.toFixed(2)}
            {localItems.length > 0 && <span className="text-yellow-600 ml-2 font-medium">(Hay items pendientes)</span>}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          {consumo?.estado === 'abierto' && !isCheckoutMode && (
            <div className="grid gap-4">
              <div className="flex flex-col sm:flex-row sm:items-end gap-2">
                <div className="grid gap-1.5 flex-grow w-full">
                  <Label htmlFor="articulo">Artículo</Label>
                  <Select onValueChange={setSelectedArticuloId} value={selectedArticuloId}>
                    <SelectTrigger id="articulo" className="w-full">
                      <SelectValue placeholder="Selecciona un artículo" />
                    </SelectTrigger>
                    <SelectContent>
                      {articulos.map((articulo) => (
                        <SelectItem key={articulo.id} value={String(articulo.id)}>
                          {articulo.descripcion} - ${articulo.precio_venta.toFixed(2)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-end gap-2">
                <div className="grid gap-1.5 flex-grow w-full">
                  <Label htmlFor="observacion">Observación</Label>
                  <Input
                    id="observacion"
                    value={observacion}
                    onChange={(e) => setObservacion(e.target.value)}
                    placeholder="Opcional: Sin cebolla, punto de cocción..."
                  />
                </div>
                <div className="flex gap-2 w-full sm:w-auto">
                  <div className="grid gap-1.5 flex-grow sm:w-24">
                    <Label htmlFor="cantidad">Cantidad</Label>
                    <Input
                      id="cantidad"
                      type="number"
                      value={cantidad}
                      onChange={(e) => setCantidad(parseInt(e.target.value) || 1)}
                      min="1"
                    />
                  </div>
                  <Button onClick={handleAddDetalle} disabled={submitting || !selectedArticuloId || cantidad <= 0 || isLoadingArticulos} className="mb-[1px]">
                    {submitting || isLoadingArticulos ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    <span className="sm:hidden ml-2">Añadir</span>
                  </Button>
                </div>
              </div>
            </div>
          )}

          <h3 className="text-lg font-semibold mt-4">Artículos Consumidos</h3>
          <div className="overflow-x-auto rounded-md border">
            {(consumo?.detalles && consumo.detalles.length > 0) || localItems.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Artículo</TableHead>
                    <TableHead>Cant.</TableHead>
                    <TableHead>Precio</TableHead>
                    <TableHead className="text-right">Subtotal</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {/* Items guardados */}
                  {consumo?.detalles?.map((detalle) => (
                    <TableRow key={detalle.id}>
                      <TableCell className="whitespace-nowrap">
                        {detalle.articulo?.descripcion}
                        {detalle.observacion && <div className="text-xs text-gray-500 italic">({detalle.observacion})</div>}
                      </TableCell>
                      <TableCell>{detalle.cantidad}</TableCell>
                      <TableCell>${detalle.precio_unitario.toFixed(2)}</TableCell>
                      <TableCell className="text-right">${(detalle.cantidad * detalle.precio_unitario).toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                  {/* Items pendientes (local) */}
                  {localItems.map((item, index) => (
                    <TableRow key={`local-${index}`} className="bg-yellow-50">
                      <TableCell className="whitespace-nowrap font-medium text-yellow-700">
                        {item.articulo.descripcion} <span className="text-xs bg-yellow-200 px-1 rounded ml-1">Pendiente</span>
                        {item.observacion && <div className="text-xs text-yellow-600 italic">({item.observacion})</div>}
                      </TableCell>
                      <TableCell className="text-yellow-700">{item.cantidad}</TableCell>
                      <TableCell className="text-yellow-700">${item.articulo.precio_venta.toFixed(2)}</TableCell>
                      <TableCell className="text-right text-yellow-700">${(item.cantidad * item.articulo.precio_venta).toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="text-gray-500 p-4 text-center">No hay artículos en este consumo.</p>
            )}
          </div>

          {/* Seccion de Propina (Solo si está abierto) */}
          {consumo?.estado === 'abierto' && (
            <div className="flex flex-col sm:flex-row items-center justify-end gap-4 mt-4 p-2 bg-gray-50 rounded-lg border border-gray-100">
              <Label htmlFor="propina" className="font-medium">Propina Sugerida (%):</Label>
              <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                <Input
                  id="propina"
                  type="number"
                  min="0"
                  max="100"
                  className="w-20 text-right"
                  value={porcentajePropina}
                  onChange={(e) => setPorcentajePropina(parseFloat(e.target.value) || 0)}
                />
                <span className="text-gray-600 font-semibold min-w-[80px] text-right">
                  ${((totalConsumo * porcentajePropina) / 100).toFixed(2)}
                </span>
              </div>
            </div>
          )}

          {/* Seccion de Facturación (Si está cerrado O estamos en modo checkout) */}
          {(consumo?.estado === 'cerrado' || isCheckoutMode) && (
            <div className="flex flex-col gap-3 mt-4 p-3 bg-blue-50 rounded-lg border border-blue-100">
              <h4 className="font-semibold text-blue-900">Datos para Facturación</h4>
              <div className="flex flex-col sm:flex-row flex-wrap items-start sm:items-center gap-4 sm:gap-6">
                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <Label htmlFor="metodoPago" className="text-blue-800 whitespace-nowrap">Método de Pago:</Label>
                  <Select value={metodoPago} onValueChange={setMetodoPago}>
                    <SelectTrigger className="w-full sm:w-[140px] bg-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Efectivo">Efectivo</SelectItem>
                      <SelectItem value="Tarjeta">Tarjeta</SelectItem>
                      <SelectItem value="Transferencia">Transferencia</SelectItem>
                      <SelectItem value="QR">QR / Billetera</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="cobrarPropina"
                    checked={cobrarPropina}
                    onChange={(e) => setCobrarPropina(e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <Label htmlFor="cobrarPropina" className="text-blue-800 cursor-pointer select-none">
                    Cobrar Propina
                    {(consumo?.propina || porcentajePropina > 0) ? ` ($${consumo?.propina ? consumo.propina.toFixed(2) : ((totalConsumo * porcentajePropina) / 100).toFixed(2)})` : ''}
                  </Label>
                </div>

                <div className="ml-auto font-bold text-lg text-blue-900 w-full sm:w-auto text-right">
                  Total a Cobrar: $
                  {(
                    (consumo?.estado === 'cerrado' ? (consumo?.total || 0) : totalConsumo) +
                    (cobrarPropina ? (consumo?.propina || (totalConsumo * porcentajePropina / 100)) : 0)
                  ).toFixed(2)}
                </div>
              </div>
              {isCheckoutMode && (
                <div className="flex justify-end gap-2 mt-2 w-full">
                  <Button variant="outline" onClick={() => setIsCheckoutMode(false)} className="flex-1 sm:flex-none">Cancelar</Button>
                  <Button onClick={handleCheckout} disabled={submitting} className="flex-1 sm:flex-none">Confirmar Cobro</Button>
                </div>
              )}
            </div>
          )}
        </div>
        <div className="flex flex-col-reverse sm:flex-row justify-between items-center gap-4 mt-4 border-t pt-4">
          <div className="flex gap-2 w-full sm:w-auto justify-center sm:justify-start">
            {localItems.length > 0 ? (
              <Button onClick={handleEnviarPedido} disabled={submitting} className="flex-1 sm:flex-none bg-orange-600 hover:bg-orange-700 text-white">
                <ChefHat className="h-4 w-4 mr-2" />
                <span className="sm:inline">Enviar Pedido ({localItems.length})</span>
              </Button>
            ) : null}
          </div>

          {/* Grupo Derecha: Cerrar/Facturar */}
          <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
            {consumo?.estado === 'abierto' && !isCheckoutMode && (
              <>
                <Button variant="destructive" onClick={handleCerrarConsumo} className="w-full sm:w-auto">
                  <X className="h-4 w-4 mr-2" />
                  Cerrar Mesa
                </Button>
                <Button onClick={() => setIsCheckoutMode(true)} className="bg-green-600 hover:bg-green-700 w-full sm:w-auto">
                  <Receipt className="h-4 w-4 mr-2" />
                  Cobrar Ahora
                </Button>
              </>
            )}
            {consumo?.estado === 'cerrado' && (
              <Button onClick={handleFacturarConsumo} disabled={submitting} className="w-full sm:w-auto">
                <Receipt className="h-4 w-4 mr-2" />
                Facturar Consumo
              </Button>
            )}
            
            <Button variant="ghost" onClick={onClose} className="w-full sm:w-auto">Cerrar</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
