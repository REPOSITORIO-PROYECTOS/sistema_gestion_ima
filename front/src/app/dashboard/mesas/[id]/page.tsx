"use client"

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useMesasStore } from '@/lib/mesasStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Users, DollarSign, Receipt } from 'lucide-react';
import Link from 'next/link';

export default function MesaDetallePage() {
  const params = useParams();
  const mesaId = parseInt(params.id as string);

  const { mesas, consumos, error, fetchMesas } = useMesasStore();

  useEffect(() => {
    fetchMesas();
  }, [fetchMesas]);

  const mesa = mesas.find(m => m.id === mesaId);
  const consumosMesa = consumos.filter(c => c.id_mesa === mesaId);

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

  const consumoActivo = consumosMesa.find(c => c.estado === 'abierto');
  const consumosCerrados = consumosMesa.filter(c => c.estado === 'cerrado');

  const getEstadoColor = (estado: string) => {
    switch (estado) {
      case 'libre': return 'bg-green-100 text-green-800';
      case 'ocupada': return 'bg-red-100 text-red-800';
      case 'reservada': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getEstadoText = (estado: string) => {
    switch (estado) {
      case 'libre': return 'Libre';
      case 'ocupada': return 'Ocupada';
      case 'reservada': return 'Reservada';
      default: return estado;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

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
            <p className="text-gray-600">Detalles y historial de consumos</p>
          </div>
        </div>
        <Badge className={getEstadoColor(mesa.estado)}>
          {getEstadoText(mesa.estado)}
        </Badge>
      </div>

      {/* Información básica */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Capacidad</p>
                <p className="text-2xl font-bold text-gray-900">{mesa.capacidad} personas</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <Receipt className="h-6 w-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Consumos Totales</p>
                <p className="text-2xl font-bold text-gray-900">{consumosMesa.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <DollarSign className="h-6 w-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Facturado</p>
                <p className="text-2xl font-bold text-gray-900">
                  ${consumosCerrados.reduce((total, c) => total + c.total, 0).toFixed(2)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Consumo activo */}
      {consumoActivo && (
        <Card className="border-green-200 bg-green-50">
          <CardHeader>
            <CardTitle className="text-green-800">Consumo Activo</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <p className="text-sm text-gray-600">Inicio</p>
                <p className="font-medium">{formatDate(consumoActivo.timestamp_inicio)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Actual</p>
                <p className="font-medium text-lg">${consumoActivo.total.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Items</p>
                <p className="font-medium">{consumoActivo.detalles?.length || 0} productos</p>
              </div>
            </div>
            <Link href={`/dashboard/mesas/${mesa.id}/consumo`}>
              <Button className="w-full md:w-auto">
                Gestionar Consumo
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Historial de consumos */}
      <Card>
        <CardHeader>
          <CardTitle>Historial de Consumos</CardTitle>
        </CardHeader>
        <CardContent>
          {consumosCerrados.length === 0 ? (
            <p className="text-gray-600 text-center py-8">
              No hay consumos cerrados para esta mesa
            </p>
          ) : (
            <div className="space-y-4">
              {consumosCerrados.map((consumo) => (
                <div key={consumo.id} className="border rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-medium">Consumo #{consumo.id}</p>
                      <p className="text-sm text-gray-600">
                        {formatDate(consumo.timestamp_inicio)}
                        {consumo.timestamp_cierre && ` - ${formatDate(consumo.timestamp_cierre)}`}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-lg">${consumo.total.toFixed(2)}</p>
                      <Badge className="bg-gray-100 text-gray-800">
                        {consumo.estado === 'cerrado' ? 'Cerrado' :
                         consumo.estado === 'facturado' ? 'Facturado' : consumo.estado}
                      </Badge>
                    </div>
                  </div>

                  {consumo.detalles && consumo.detalles.length > 0 && (
                    <div className="mt-3">
                      <p className="text-sm font-medium text-gray-700 mb-2">Productos:</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {consumo.detalles.map((detalle) => (
                          <div key={detalle.id} className="text-sm bg-gray-50 p-2 rounded">
                            <span className="font-medium">{detalle.articulo?.descripcion || 'Producto'}</span>
                            <span className="text-gray-600 ml-2">
                              x{detalle.cantidad} = ${(detalle.cantidad * detalle.precio_unitario).toFixed(2)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}