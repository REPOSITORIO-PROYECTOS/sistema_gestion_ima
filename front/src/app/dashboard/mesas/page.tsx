"use client"

import { useEffect, useState } from 'react';
import { useMesasStore } from '@/lib/mesasStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Loader2, Plus, Edit, Trash2, Users, Eye, EyeOff, RefreshCw, Receipt, Printer } from 'lucide-react';
import { TicketModal } from '@/components/TicketModal';
import { routeToDepartments } from '@/lib/ticketRoutingService';
import type { TicketResponse } from '@/lib/types/mesas';
// ...existing imports...

import type { Mesa } from '@/lib/types/mesas';
import Link from 'next/link';

export default function MesasPage() {
  const [ticketModalOpen, setTicketModalOpen] = useState(false);
  const [currentTicket, setCurrentTicket] = useState<TicketResponse | null>(null);
  const handleImprimirComanda = async (mesaId: number) => {
    const consumoActivo = consumos.find(c => c.id_mesa === mesaId && c.estado === 'abierto');
    if (!consumoActivo) return;
    const ticket = await generarTicket({ id_consumo_mesa: consumoActivo.id });
    if (ticket) {
      setCurrentTicket(ticket);
      setTicketModalOpen(true);
      routeToDepartments(ticket);
    }
  };
  const [selectedMesas, setSelectedMesas] = useState<number[]>([]);

  // Alternar selección de una mesa
  const toggleSelectMesa = (id: number) => {
    setSelectedMesas((prev) =>
      prev.includes(id) ? prev.filter((mid) => mid !== id) : [...prev, id]
    );
    setTimeout(() => localStorage.setItem('mesas:selected', JSON.stringify(selectedMesas)), 0);
  };

  // Seleccionar todas
  const selectAllMesas = () => {
    setSelectedMesas(mesas.map((m) => m.id));
  };

  // Deseleccionar todas
  const deselectAllMesas = () => {
    setSelectedMesas([]);
  };
  const {
    mesas,
    mesaLogs,
    consumos,
    loading,
    error,
    fetchMesas,
    createMesa,
    updateMesa,
    deleteMesa,
    fetchMesaLogs,
    fetchConsumos,
    generarTicket
  } = useMesasStore();

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [editingMesa, setEditingMesa] = useState<Mesa | null>(null);
  const [formData, setFormData] = useState({
    numero: '',
    capacidad: '4',
    estado: 'LIBRE' as 'LIBRE' | 'OCUPADA' | 'RESERVADA',
  });
  const [localError, setLocalError] = useState<string | null>(null);
  const [numeroError, setNumeroError] = useState<string | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem('mesas:selected');
    if (saved) {
      try { setSelectedMesas(JSON.parse(saved)); } catch {}
    }
    fetchMesas();
    fetchMesaLogs();
    fetchConsumos();
    const interval = setInterval(() => {
      fetchMesas();
      fetchConsumos();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchMesas, fetchMesaLogs, fetchConsumos]);

  // Función para validar número de mesa en tiempo real
  const validarNumeroMesa = (numero: string, excludeId?: number): string | null => {
    const num = parseInt(numero);
    if (isNaN(num) || num <= 0) {
      return 'El número de mesa debe ser un número positivo';
    }

    // Verificar si el número ya existe (excluyendo la mesa actual si estamos editando)
    const mesaExistente = mesas.find(m => m.numero === num && m.id !== excludeId);
    if (mesaExistente) {
      return `Ya existe una mesa con el número ${num}. ${mesaExistente.activo ? 'Está activa' : 'Está inactiva y requiere revisión'}.`;
    }

    return null;
  };

  // Función para manejar cambios en el número de mesa con validación en tiempo real
  const handleNumeroChange = (value: string, excludeId?: number) => {
    setFormData(prev => ({ ...prev, numero: value }));
    const error = validarNumeroMesa(value, excludeId);
    setNumeroError(error);
  };

  // Calcular el próximo número disponible cuando se abre el diálogo
  const getProximoNumeroDisponible = () => {
    const numerosExistentes = mesas.map(m => m.numero).sort((a, b) => a - b);
    let numero = 1;
    while (numerosExistentes.includes(numero)) {
      numero++;
    }
    return numero;
  };

  const handleOpenCreateDialog = () => {
    const proximoNumero = getProximoNumeroDisponible();
    setFormData({
      numero: proximoNumero.toString(),
      capacidad: '4',
      estado: 'LIBRE',
    });
    setLocalError(null);
    setNumeroError(null);
    setIsCreateDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      numero: '',
      capacidad: '4',
      estado: 'LIBRE',
    });
    setEditingMesa(null);
    setLocalError(null);
    setNumeroError(null);
  };

  const handleCreate = async () => {
    setLocalError(null);

    const numero = parseInt(formData.numero);
    const capacidad = parseInt(formData.capacidad);

    // Validar número de mesa
    const numeroError = validarNumeroMesa(formData.numero);
    if (numeroError) {
      setLocalError(numeroError);
      return;
    }

    if (isNaN(capacidad) || capacidad <= 0) {
      setLocalError('La capacidad debe ser un número positivo');
      return;
    }

    const success = await createMesa({
      numero,
      capacidad,
      activo: true,
    });

    if (success) {
      setIsCreateDialogOpen(false);
      resetForm();
    } else {
      // El error ya está establecido en el store, pero podemos mostrarlo localmente también
      setLocalError(error);
    }
  };

  const handleEdit = (mesa: Mesa) => {
    setEditingMesa(mesa);
    setFormData({
      numero: mesa.numero.toString(),
      capacidad: mesa.capacidad.toString(),
      estado: mesa.estado,
    });
    setLocalError(null);
    setNumeroError(null);
  };

  const handleUpdate = async () => {
    if (!editingMesa) return;

    setLocalError(null);

    const numero = parseInt(formData.numero);
    const capacidad = parseInt(formData.capacidad);

    // Validar número de mesa (excluyendo la mesa actual)
    const numeroError = validarNumeroMesa(formData.numero, editingMesa.id);
    if (numeroError) {
      setLocalError(numeroError);
      return;
    }

    if (isNaN(capacidad) || capacidad <= 0) {
      setLocalError('La capacidad debe ser un número positivo');
      return;
    }

    // Registrar cambio de estado si cambió
    const estadoCambio = formData.estado !== editingMesa.estado;
    const numeroCambio = numero !== editingMesa.numero;

    const success = await updateMesa(editingMesa.id, {
      numero,
      capacidad,
      estado: formData.estado,
    });

    if (success) {
      // Si hubo cambios, recargar logs
      if (estadoCambio || numeroCambio) {
        fetchMesaLogs();
      }
      setEditingMesa(null);
      resetForm();
    } else {
      setLocalError(error);
    }
  };

  const handleDelete = async (id: number) => {
    if (confirm('¿Estás seguro de que quieres eliminar esta mesa? Esta acción no se puede deshacer.')) {
      await deleteMesa(id);
    }
  };

  const toggleMesaStatus = async (mesa: Mesa) => {
    const newStatus = mesa.activo ? false : true;
    const success = await updateMesa(mesa.id, { activo: newStatus });
    if (success) {
      // Recargar logs ya que cambió el estado activo
      fetchMesaLogs();
    }
  };

  const getEstadoColor = (estado: string) => {
    switch (estado) {
      case 'LIBRE': return 'bg-green-100 text-green-800';
      case 'OCUPADA': return 'bg-red-100 text-red-800';
      case 'RESERVADA': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getEstadoText = (estado: string) => {
    switch (estado) {
      case 'LIBRE': return 'Libre';
      case 'OCUPADA': return 'Ocupada';
      case 'RESERVADA': return 'Reservada';
      default: return 'Desconocido';
    }
  };

  // Función para obtener información del consumo de una mesa
  const getConsumoInfo = (mesaId: number) => {
    const consumoActivo = consumos.find(c => c.id_mesa === mesaId && c.estado === 'abierto');
    return consumoActivo ? {
      tieneConsumo: true,
      total: consumoActivo.total,
      tiempo: new Date(consumoActivo.timestamp_inicio).toLocaleTimeString('es-ES', {
        hour: '2-digit',
        minute: '2-digit'
      })
    } : {
      tieneConsumo: false,
      total: 0,
      tiempo: ''
    };
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Administración de Mesas</h1>
          <p className="text-gray-600">Gestiona todas las mesas del restaurante (activas e inactivas)</p>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchMesas} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>

          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={handleOpenCreateDialog}>
                <Plus className="h-4 w-4 mr-2" />
                Nueva Mesa
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Crear Nueva Mesa</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                {localError && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-red-600 text-sm">{localError}</p>
                  </div>
                )}

                <div>
                  <Label htmlFor="numero">Número de Mesa</Label>
                  <Input
                    id="numero"
                    type="number"
                    value={formData.numero}
                    onChange={(e) => handleNumeroChange(e.target.value)}
                    placeholder="Ej: 1"
                    min="1"
                    className={numeroError ? 'border-red-500' : ''}
                  />
                  {numeroError && (
                    <p className="text-red-500 text-sm mt-1">{numeroError}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="capacidad">Capacidad</Label>
                  <Input
                    id="capacidad"
                    type="number"
                    value={formData.capacidad}
                    onChange={(e) => setFormData(prev => ({ ...prev, capacidad: e.target.value }))}
                    placeholder="Ej: 4"
                    min="1"
                  />
                </div>

                <div className="flex gap-2 pt-4">
                  <Button onClick={handleCreate} disabled={loading} className="flex-1">
                    {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                    Crear Mesa
                  </Button>
                  <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                    Cancelar
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Estadísticas rápidas */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Users className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Mesas</p>
                <p className="text-2xl font-bold text-gray-900">{mesas.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <Users className="h-6 w-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Libres</p>
                <p className="text-2xl font-bold text-green-600">
                  {mesas.filter(m => m.estado === 'LIBRE').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center">
              <div className="p-2 bg-red-100 rounded-lg">
                <Users className="h-6 w-6 text-red-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Ocupadas</p>
                <p className="text-2xl font-bold text-red-600">
                  {mesas.filter(m => m.estado === 'OCUPADA').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Users className="h-6 w-6 text-yellow-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Reservadas</p>
                <p className="text-2xl font-bold text-yellow-600">
                  {mesas.filter(m => m.estado === 'RESERVADA').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center">
              <div className="p-2 bg-orange-100 rounded-lg">
                <Users className="h-6 w-6 text-orange-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Requieren Revisión</p>
                <p className="text-2xl font-bold text-orange-600">
                  {mesas.filter(m => !m.activo).length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Receipt className="h-6 w-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Con Consumo Activo</p>
                <p className="text-2xl font-bold text-purple-600">
                  {consumos.filter(c => c.estado === 'abierto').length}
                </p>
                <p className="text-xs text-gray-500">
                  Total: ${consumos.filter(c => c.estado === 'abierto').reduce((sum, c) => sum + c.total, 0).toFixed(2)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Mapa visual de mesas */}
      <Card>
        <CardHeader>
          <CardTitle>Mapa de Mesas (selecciona una o varias)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 p-2">
            {mesas.map((mesa) => (
              <div
                key={mesa.id}
                className={`flex flex-col items-center justify-center border rounded-lg p-4 cursor-pointer transition-all duration-150 shadow-sm w-28 h-28
                  ${selectedMesas.includes(mesa.id) ? 'bg-blue-100 border-blue-400 ring-2 ring-blue-400' : 'bg-white hover:bg-blue-50'}
                  ${!mesa.activo ? 'opacity-50 pointer-events-none' : ''}`}
                onClick={() => mesa.activo && toggleSelectMesa(mesa.id)}
                title={mesa.activo ? `Mesa ${mesa.numero}` : 'Mesa inactiva'}
              >
                <span className="text-2xl font-bold">{mesa.numero}</span>
                <span className="text-xs text-gray-500">{mesa.capacidad} pers.</span>
                <span className={`mt-2 text-xs px-2 py-1 rounded ${mesa.estado === 'LIBRE' ? 'bg-green-100 text-green-700' : mesa.estado === 'OCUPADA' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>{getEstadoText(mesa.estado)}</span>
                {selectedMesas.includes(mesa.id) && <span className="mt-1 text-blue-600 text-xs font-semibold">Seleccionada</span>}
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-4">
            <Button variant="outline" size="sm" onClick={selectAllMesas}>Seleccionar todas</Button>
            <Button variant="outline" size="sm" onClick={deselectAllMesas}>Deseleccionar todas</Button>
            <span className="text-sm text-gray-600 ml-2">{selectedMesas.length} mesa(s) seleccionada(s)</span>
            {selectedMesas.length === 1 && (
              <Button size="sm" className="ml-auto" onClick={() => handleImprimirComanda(selectedMesas[0])}>
                <Printer className="h-4 w-4 mr-2" />
                Confirmar y Ticket
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Lista de Mesas</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : mesas.length === 0 ? (
            <div className="text-center py-12">
              <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No hay mesas configuradas</h3>
              <p className="text-gray-600 mb-4">
                Comienza creando tu primera mesa para gestionar los consumos de tus clientes.
              </p>
              <Button onClick={handleOpenCreateDialog}>
                <Plus className="h-4 w-4 mr-2" />
                Crear Primera Mesa
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>
                    <input
                      type="checkbox"
                      checked={selectedMesas.length === mesas.length && mesas.length > 0}
                      onChange={e => e.target.checked ? selectAllMesas() : deselectAllMesas()}
                      aria-label="Seleccionar todas"
                    />
                  </TableHead>
                  <TableHead>Número</TableHead>
                  <TableHead>Capacidad</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Activo</TableHead>
                  <TableHead>Consumo Actual</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mesas.map((mesa) => (
                  <TableRow key={mesa.id} className={selectedMesas.includes(mesa.id) ? 'bg-blue-50' : ''}>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={selectedMesas.includes(mesa.id)}
                        onChange={() => toggleSelectMesa(mesa.id)}
                        aria-label={`Seleccionar mesa ${mesa.numero}`}
                        disabled={!mesa.activo}
                      />
                    </TableCell>
                    <TableCell className="font-medium">Mesa {mesa.numero}</TableCell>
                    <TableCell>{mesa.capacidad} personas</TableCell>
                    <TableCell>
                      <Badge className={getEstadoColor(mesa.estado)}>
                        {getEstadoText(mesa.estado)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Badge className={mesa.activo ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'}>
                          {mesa.activo ? 'Activo' : 'Revisar'}
                        </Badge>
                        {!mesa.activo && (
                          <span className="text-xs text-orange-600 font-medium">⚠️ Requiere atención</span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {(() => {
                        const consumoInfo = getConsumoInfo(mesa.id);
                        return consumoInfo.tieneConsumo ? (
                          <div className="text-sm flex flex-col gap-1">
                            <div className="font-medium text-green-600">
                              ${consumoInfo.total.toFixed(2)}
                            </div>
                            <div className="text-gray-500">
                              Desde {consumoInfo.tiempo}
                            </div>
                            <Button variant="ghost" size="sm" className="mt-1 px-2 py-1 h-7 w-fit" title="Imprimir comanda"
                              onClick={() => handleImprimirComanda(mesa.id)}>
                              <Printer className="h-4 w-4 mr-1" />
                              Ticket
                            </Button>
                          </div>
                        ) : (
                          <span className="text-gray-400 text-sm">Sin consumo</span>
                        );
                      })()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        {mesa.estado === 'LIBRE' && mesa.activo && (
                          <Link href={`/dashboard/mesas/${mesa.id}/consumo`}>
                            <Button variant="outline" size="sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                        )}

                        {mesa.estado === 'OCUPADA' && mesa.activo && (
                          <Link href={`/dashboard/mesas/${mesa.id}/consumo`}>
                            <Button variant="outline" size="sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                        )}

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => toggleMesaStatus(mesa)}
                          disabled={loading}
                          title={mesa.activo ? 'Desactivar mesa' : 'Activar mesa'}
                        >
                          {mesa.activo ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEdit(mesa)}
                          disabled={loading}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDelete(mesa.id)}
                          disabled={loading}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Registro de Cambios de Estado */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            Registro de Cambios de Estado
          </CardTitle>
          <p className="text-sm text-gray-600">
            Historial de cambios en el estado de las mesas
          </p>
        </CardHeader>
        <CardContent>
          {mesaLogs.length === 0 ? (
            <div className="text-center py-8">
              <RefreshCw className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No hay registros de cambios</h3>
              <p className="text-gray-600">
                Los cambios de estado de las mesas aparecerán aquí.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {mesaLogs.slice(0, 10).map((log) => (
                <div key={log.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-4">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <RefreshCw className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium">
                        Mesa {log.mesa?.numero || log.id_mesa}
                      </p>
                      <p className="text-sm text-gray-600">
                        {log.estado_anterior ? `${log.estado_anterior} → ${log.estado_nuevo}` : `Estado inicial: ${log.estado_nuevo}`}
                        {log.activo_anterior !== null && log.activo_anterior !== log.activo_nuevo && (
                          <span className="ml-2">
                            ({log.activo_anterior ? 'Activado' : 'Desactivado'} → {log.activo_nuevo ? 'Activado' : 'Desactivado'})
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-500">
                      {new Date(log.timestamp).toLocaleString('es-ES')}
                    </p>
                  </div>
                </div>
              ))}
              {mesaLogs.length > 10 && (
                <div className="text-center pt-4">
                  <p className="text-sm text-gray-600">
                    Mostrando los últimos 10 cambios. Total: {mesaLogs.length} registros.
                  </p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialog de edición */}
      <Dialog open={!!editingMesa} onOpenChange={() => setEditingMesa(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Mesa {editingMesa?.numero}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {localError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-red-600 text-sm">{localError}</p>
              </div>
            )}

            <div>
              <Label htmlFor="edit-numero">Número de Mesa</Label>
              <Input
                id="edit-numero"
                type="number"
                value={formData.numero}
                onChange={(e) => handleNumeroChange(e.target.value, editingMesa?.id)}
                min="1"
                className={numeroError ? 'border-red-500' : ''}
              />
              {numeroError && (
                <p className="text-red-500 text-sm mt-1">{numeroError}</p>
              )}
            </div>

            <div>
              <Label htmlFor="edit-capacidad">Capacidad</Label>
              <Input
                id="edit-capacidad"
                type="number"
                value={formData.capacidad}
                onChange={(e) => setFormData(prev => ({ ...prev, capacidad: e.target.value }))}
                min="1"
              />
            </div>

            <div>
              <Label htmlFor="edit-estado">Estado</Label>
              <Select value={formData.estado} onValueChange={(value: 'LIBRE' | 'OCUPADA' | 'RESERVADA') => setFormData(prev => ({ ...prev, estado: value }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="LIBRE">Libre</SelectItem>
                  <SelectItem value="OCUPADA">Ocupada</SelectItem>
                  <SelectItem value="RESERVADA">Reservada</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-2 pt-4">
              <Button onClick={handleUpdate} disabled={loading} className="flex-1">
                {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Actualizar Mesa
              </Button>
              <Button variant="outline" onClick={() => setEditingMesa(null)}>
                Cancelar
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

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
