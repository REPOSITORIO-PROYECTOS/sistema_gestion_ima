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
  const [porcentajePropina, setPorcentajePropina] = useState<number>(10);
  const [metodoPago, setMetodoPago] = useState<string>('Efectivo');
  const [cobrarPropina, setCobrarPropina] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState(false);
  const [isCheckoutMode, setIsCheckoutMode] = useState(false);

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

    setSubmitting(true);
    const result = await addDetalleConsumo(consumo.id, {
      id_articulo: parseInt(selectedArticuloId),
      cantidad,
      precio_unitario: latest.precio_venta,
      descuento_aplicado: 0,
    });
    setSubmitting(false);
    if (result.ok) {
      toast.success('Artículo agregado al consumo.');

      // Imprimir automáticamente comanda individual
      const ticketItem: TicketResponse = {
        mesa_numero: consumo.mesa?.numero || 0,
        timestamp: new Date().toISOString(),
        detalles: [{
          articulo: articulo.descripcion,
          cantidad: cantidad,
          precio_unitario: articulo.precio_venta,
          subtotal: cantidad * articulo.precio_venta,
          categoria: (articulo as any).categoria?.nombre || null // Intentar obtener categoría si existe
        }],
        total: cantidad * articulo.precio_venta,
        propina: 0,
        porcentaje_propina: 0,
        total_con_propina: cantidad * articulo.precio_venta
      };
      routeToDepartments(ticketItem);
      toast.success('Comanda enviada automáticamente.');

      setSelectedArticuloId('');
      setCantidad(1);
      fetchConsumos(); // Para actualizar el consumo en el store
    } else {
      toast.error(result.error || error || 'Error al agregar artículo.');
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
        toast.success('Consumo facturado exitosamente.');
        onClose();
      } else {
        toast.error(error || 'Error al facturar consumo.');
      }
    }
  };

  const handleImprimirComanda = async () => {
    if (!consumo) return;
    toast.info("Enviando a cocina...");
    // 'comanda' debe ser un formato que tu backend entienda para imprimir solo lo nuevo
    const ticket = await generarTicket({ id_consumo_mesa: consumo.id, formato: 'ticket' });
    if (ticket) {
      routeToDepartments(ticket);
      toast.success("Comanda enviada correctamente");
    }
  };

  const handleImprimirPrecuenta = async () => {
    if (!consumo) return;
    toast.info("Imprimiendo pre-cuenta...");
    // 'comprobante' o 'precuenta' según tu backend
    const ticket = await generarTicket({ id_consumo_mesa: consumo.id, formato: 'comprobante' });
    if (ticket) toast.success("Pre-cuenta generada");
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

  const totalConsumo = consumo?.detalles?.reduce((sum, detalle) => sum + (detalle.cantidad * detalle.precio_unitario), 0) || 0;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Consumo de Mesa {consumo?.mesa?.numero}</DialogTitle>
          <DialogDescription>
            Detalles del consumo actual. Total: ${totalConsumo.toFixed(2)}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          {consumo?.estado === 'abierto' && !isCheckoutMode && (
            <div className="flex items-end gap-2">
              <div className="grid gap-1.5 flex-grow">
                <Label htmlFor="articulo">Artículo</Label>
                <Select onValueChange={setSelectedArticuloId} value={selectedArticuloId}>
                  <SelectTrigger id="articulo">
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
              <div className="grid gap-1.5 w-24">
                <Label htmlFor="cantidad">Cantidad</Label>
                <Input
                  id="cantidad"
                  type="number"
                  value={cantidad}
                  onChange={(e) => setCantidad(parseInt(e.target.value) || 1)}
                  min="1"
                />
              </div>
              <Button onClick={handleAddDetalle} disabled={submitting || !selectedArticuloId || cantidad <= 0 || isLoadingArticulos}>
                {submitting || isLoadingArticulos ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Añadir
              </Button>
            </div>
          )}

          <h3 className="text-lg font-semibold mt-4">Artículos Consumidos</h3>
          {consumo?.detalles && consumo.detalles.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Artículo</TableHead>
                  <TableHead>Cantidad</TableHead>
                  <TableHead>Precio Unitario</TableHead>
                  <TableHead className="text-right">Subtotal</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {consumo.detalles.map((detalle) => (
                  <TableRow key={detalle.id}>
                    <TableCell>{detalle.articulo?.descripcion}</TableCell>
                    <TableCell>{detalle.cantidad}</TableCell>
                    <TableCell>${detalle.precio_unitario.toFixed(2)}</TableCell>
                    <TableCell className="text-right">${(detalle.cantidad * detalle.precio_unitario).toFixed(2)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-gray-500">No hay artículos en este consumo.</p>
          )}

          {/* Seccion de Propina (Solo si está abierto) */}
          {consumo?.estado === 'abierto' && (
             <div className="flex items-center justify-end gap-4 mt-4 p-2 bg-gray-50 rounded-lg border border-gray-100">
                <Label htmlFor="propina" className="font-medium">Propina Sugerida (%):</Label>
                <div className="flex items-center gap-2">
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
                <div className="flex flex-wrap items-center gap-6">
                    <div className="flex items-center gap-2">
                        <Label htmlFor="metodoPago" className="text-blue-800">Método de Pago:</Label>
                        <Select value={metodoPago} onValueChange={setMetodoPago}>
                            <SelectTrigger className="w-[140px] bg-white">
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
                        <Label htmlFor="cobrarPropina" className="text-blue-800 cursor-pointer">
                            Cobrar Propina 
                            {(consumo?.propina || porcentajePropina > 0) ? ` ($${consumo?.propina ? consumo.propina.toFixed(2) : ((totalConsumo * porcentajePropina) / 100).toFixed(2)})` : ''}
                        </Label>
                    </div>

                    <div className="ml-auto font-bold text-lg text-blue-900">
                        Total a Cobrar: $
                        {(
                            (consumo?.estado === 'cerrado' ? (consumo?.total || 0) : totalConsumo) + 
                            (cobrarPropina ? (consumo?.propina || (totalConsumo * porcentajePropina / 100)) : 0)
                        ).toFixed(2)}
                    </div>
                </div>
                {isCheckoutMode && (
                    <div className="flex justify-end gap-2 mt-2">
                        <Button variant="outline" onClick={() => setIsCheckoutMode(false)}>Cancelar</Button>
                        <Button onClick={handleCheckout} disabled={submitting}>Confirmar Cobro</Button>
                    </div>
                )}
             </div>
          )}
        </div>
     <div className="flex justify-between items-center mt-4 border-t pt-4">
        {/* Grupo Izquierda: Acciones de Impresión */}
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={handleImprimirComanda}>
            <ChefHat className="h-4 w-4 mr-2" />
            Marcha (Cocina)
          </Button>
          <Button variant="outline" size="sm" onClick={handleImprimirPrecuenta}>
            <FileText className="h-4 w-4 mr-2" />
            Pre-cuenta
          </Button>
        </div>

        {/* Grupo Derecha: Cerrar/Facturar */}
        <div className="flex gap-2">
           {consumo?.estado === 'abierto' && !isCheckoutMode && (
             <>
                <Button variant="destructive" onClick={handleCerrarConsumo}>
                    <X className="h-4 w-4 mr-2" />
                    Cerrar Mesa
                </Button>
                <Button onClick={() => setIsCheckoutMode(true)} className="bg-green-600 hover:bg-green-700">
                    <Receipt className="h-4 w-4 mr-2" />
                    Cobrar Ahora
                </Button>
             </>
          )}
          {consumo?.estado === 'cerrado' && (
            <Button onClick={handleFacturarConsumo} disabled={submitting}>
              <Receipt className="h-4 w-4 mr-2" />
              Facturar Consumo
            </Button>
          )}
          {(consumo?.estado === 'cerrado' || consumo?.estado === 'facturado') && (
            <Button onClick={async () => {
              if (consumo) {
                const ticket = await generarTicket({ id_consumo_mesa: consumo.id, formato: 'ticket' });
                if (ticket) {
                  onTicketGenerated(ticket);
                }
              }
            }} disabled={submitting}>
              <Receipt className="h-4 w-4 mr-2" />
              Generar Ticket
            </Button>
          )}
          <Button variant="ghost" onClick={onClose}>Cerrar</Button>
        </div>
      </div>
    </DialogContent>
    </Dialog>
  );
};
