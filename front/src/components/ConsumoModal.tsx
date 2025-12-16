import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Loader2, Plus, X, Receipt, Printer } from 'lucide-react';
import { useMesasStore } from '@/lib/mesasStore';
import { useAuthStore } from '@/lib/authStore';
import { api } from '@/lib/api-client';
import type { ConsumoMesa, Articulo, TicketResponse } from '@/lib/types/mesas';
import { toast } from 'sonner';

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
  const [submitting, setSubmitting] = useState(false);

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

    setSubmitting(true);
    const success = await addDetalleConsumo(consumo.id, {
      id_articulo: parseInt(selectedArticuloId),
      cantidad,
      precio_unitario: articulo.precio_venta,
    });
    setSubmitting(false);
    if (success) {
      toast.success('Artículo agregado al consumo.');
      setSelectedArticuloId('');
      setCantidad(1);
      fetchConsumos(); // Para actualizar el consumo en el store
    } else {
      toast.error(error || 'Error al agregar artículo.');
    }
  };

  const handleCerrarConsumo = async () => {
    if (!consumo) return;
    if (confirm('¿Estás seguro de que quieres cerrar este consumo?')) {
      setSubmitting(true);
      const success = await cerrarConsumo(consumo.id);
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
      const success = await facturarConsumo(consumo.id);
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
    if (ticket) toast.success("Comanda enviada correctamente");
  };

  const handleImprimirPrecuenta = async () => {
    if (!consumo) return;
    toast.info("Imprimiendo pre-cuenta...");
    // 'comprobante' o 'precuenta' según tu backend
    const ticket = await generarTicket({ id_consumo_mesa: consumo.id, formato: 'comprobante' });
    if (ticket) toast.success("Pre-cuenta generada");
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
          {consumo?.estado === 'abierto' && (
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
        </div>
     <div className="flex justify-between items-center mt-4 border-t pt-4">
        {/* Grupo Izquierda: Acciones de Impresión */}
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={handleImprimirComanda}>
            <Printer className="h-4 w-4 mr-2" />
            Marcha (Cocina)
          </Button>
          <Button variant="outline" size="sm" onClick={handleImprimirPrecuenta}>
            <Receipt className="h-4 w-4 mr-2" />
            Pre-cuenta
          </Button>
        </div>

        {/* Grupo Derecha: Cerrar/Facturar */}
        <div className="flex gap-2">
           {consumo?.estado === 'abierto' && (
             <Button variant="destructive" onClick={handleCerrarConsumo}>
               <X className="h-4 w-4 mr-2" />
              Cerrar Consumo
            </Button>
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
