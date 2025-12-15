"use client"

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useMesasStore } from '@/lib/mesasStore';
import { useProductosStore } from '@/lib/productosStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Loader2, Plus, Receipt, ArrowLeft } from 'lucide-react';
import { TicketModal } from '@/components/TicketModal';
import { routeToDepartments } from '@/lib/ticketRoutingService';
import Link from 'next/link';
import type { ConsumoMesa, TicketResponse } from '@/lib/types/mesas';

export default function ConsumoMesaPage() {
  const params = useParams();
  const mesaId = parseInt(params.id as string);

  const {
    mesas,
    consumos,
    loading,
    error,
    createConsumo,
    addDetalleConsumo,
    cerrarConsumo,
    generarTicket
  } = useMesasStore();

  const {
    productos,
    loading: loadingProductos,
    fetchProductos
  } = useProductosStore();

  const [selectedProducto, setSelectedProducto] = useState<string>('');
  const [cantidad, setCantidad] = useState<string>('1');
  const [consumoActual, setConsumoActual] = useState<ConsumoMesa | null>(null);
  const [ticketModalOpen, setTicketModalOpen] = useState(false);
  const [currentTicket, setCurrentTicket] = useState<TicketResponse | null>(null);

  const mesa = mesas.find(m => m.id === mesaId);
  const consumoActivo = consumos.find(c => c.id_mesa === mesaId && c.estado === 'abierto');

  useEffect(() => {
    if (consumoActivo) {
      setConsumoActual(consumoActivo);
    }
  }, [consumoActivo]);

  // Cargar productos al montar el componente
  useEffect(() => {
    fetchProductos();
  }, [fetchProductos]);

  const handleAbrirConsumo = async () => {
    if (!mesa) return;

    const nuevoConsumo = await createConsumo({
      id_mesa: mesa.id,
      id_usuario: 1, // TODO: Obtener del store de auth
      id_empresa: mesa.id_empresa,
    });

    if (nuevoConsumo) {
      setConsumoActual(nuevoConsumo);
    }
  };

  const handleAgregarProducto = async () => {
    if (!consumoActual || !selectedProducto) return;

    const producto = productos.find(p => p.id.toString() === selectedProducto);
    if (!producto) return;

    const cantidadNum = parseFloat(cantidad);
    if (isNaN(cantidadNum) || cantidadNum <= 0) return;

    const success = await addDetalleConsumo(consumoActual.id, {
      id_articulo: producto.id,
      cantidad: cantidadNum,
      precio_unitario: producto.precio_venta,
      descuento_aplicado: 0,
    });

    if (success) {
      setSelectedProducto('');
      setCantidad('1');
      // El store se actualizará automáticamente
    }
  };

  const handleCerrarConsumo = async () => {
    if (!consumoActual) return;

    const success = await cerrarConsumo(consumoActual.id);
    if (success) {
      setConsumoActual(null);
    }
  };

  const handleGenerarTicket = async () => {
    if (!consumoActual) return;

    const ticket = await generarTicket({ id_consumo_mesa: consumoActual.id });
    if (ticket) {
      setCurrentTicket(ticket);
      setTicketModalOpen(true);
      routeToDepartments(ticket);
    }
  };

  if (!mesa) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <p className="text-red-600 mb-4">Mesa no encontrada</p>
        <Link href="/dashboard/mesas">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Mesas
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <Link href="/dashboard/mesas">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Volver
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Mesa {mesa.numero}</h1>
            <p className="text-gray-600">Capacidad: {mesa.capacidad} personas</p>
          </div>
        </div>
        <Badge className={
          mesa.estado === 'LIBRE' ? 'bg-green-100 text-green-800' :
          mesa.estado === 'OCUPADA' ? 'bg-red-100 text-red-800' :
          'bg-yellow-100 text-yellow-800'
        }>
          {mesa.estado === 'LIBRE' ? 'Libre' :
           mesa.estado === 'OCUPADA' ? 'Ocupada' : 'Reservada'}
        </Badge>
      </div>

      {/* Estado del consumo */}
      {!consumoActual ? (
        <Card>
          <CardContent className="p-6 text-center">
            <h3 className="text-lg font-medium mb-4">No hay consumo activo</h3>
            <p className="text-gray-600 mb-6">
              Abre un consumo para comenzar a agregar productos a esta mesa.
            </p>
            <Button onClick={handleAbrirConsumo} disabled={loading}>
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Abrir Consumo
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Panel de agregar productos */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle>Agregar Producto</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="producto">Producto</Label>
                <Select value={selectedProducto} onValueChange={setSelectedProducto}>
                  <SelectTrigger>
                    <SelectValue placeholder="Seleccionar producto" />
                  </SelectTrigger>
                  <SelectContent>
                    {productos.map((producto) => (
                      <SelectItem key={producto.id} value={producto.id.toString()}>
                        {producto.descripcion} - ${producto.precio_venta}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="cantidad">Cantidad</Label>
                <Input
                  id="cantidad"
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={cantidad}
                  onChange={(e) => setCantidad(e.target.value)}
                />
              </div>

              <Button
                onClick={handleAgregarProducto}
                disabled={loading || loadingProductos || !selectedProducto}
                className="w-full"
              >
                {(loading || loadingProductos) && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                <Plus className="h-4 w-4 mr-2" />
                Agregar
              </Button>
            </CardContent>
          </Card>

          {/* Lista de productos del consumo */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Consumo Actual</CardTitle>
            </CardHeader>
            <CardContent>
              {consumoActual.detalles && consumoActual.detalles.length > 0 ? (
                <div className="space-y-4">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Producto</TableHead>
                        <TableHead className="text-center">Cantidad</TableHead>
                        <TableHead className="text-right">Precio Unit.</TableHead>
                        <TableHead className="text-right">Subtotal</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {consumoActual.detalles.map((detalle) => (
                        <TableRow key={detalle.id}>
                          <TableCell>{detalle.articulo?.descripcion || 'Producto'}</TableCell>
                          <TableCell className="text-center">{detalle.cantidad}</TableCell>
                          <TableCell className="text-right">${detalle.precio_unitario}</TableCell>
                          <TableCell className="text-right">
                            ${(detalle.cantidad * detalle.precio_unitario).toFixed(2)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  <div className="flex justify-between items-center pt-4 border-t">
                    <div className="text-lg font-semibold">
                      Total: ${consumoActual.total.toFixed(2)}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={handleGenerarTicket}
                        disabled={loading}
                      >
                        <Receipt className="h-4 w-4 mr-2" />
                        Ticket
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={handleCerrarConsumo}
                        disabled={loading}
                      >
                        {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                        Cerrar Consumo
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-gray-600 text-center py-8">
                  No hay productos agregados al consumo
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      <TicketModal
        ticket={currentTicket}
        isOpen={ticketModalOpen}
        onClose={() => setTicketModalOpen(false)}
      />
    </div>
  );
}
