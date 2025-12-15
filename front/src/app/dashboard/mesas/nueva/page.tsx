"use client"

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMesasStore } from '@/lib/mesasStore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, ArrowLeft, Plus } from 'lucide-react';
import Link from 'next/link';

export default function NuevaMesaPage() {
  const router = useRouter();
  const { createMesa, loading, error } = useMesasStore();

  const [formData, setFormData] = useState({
    numero: '',
    capacidad: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const numero = parseInt(formData.numero);
    const capacidad = parseInt(formData.capacidad);

    if (isNaN(numero) || numero <= 0) {
      alert('El número de mesa debe ser un número positivo');
      return;
    }

    if (isNaN(capacidad) || capacidad <= 0) {
      alert('La capacidad debe ser un número positivo');
      return;
    }

    const success = await createMesa({
      numero,
      capacidad,
    });

    if (success) {
      router.push('/dashboard/mesas');
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard/mesas">
          <Button variant="outline" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Nueva Mesa</h1>
          <p className="text-gray-600">Crear una nueva mesa para el restaurante</p>
        </div>
      </div>

      {/* Formulario */}
      <div className="max-w-md">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              Información de la Mesa
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="numero">Número de Mesa</Label>
                <Input
                  id="numero"
                  type="number"
                  value={formData.numero}
                  onChange={(e) => handleInputChange('numero', e.target.value)}
                  placeholder="Ej: 1"
                  min="1"
                  required
                />
                <p className="text-sm text-gray-500 mt-1">
                  Número único para identificar la mesa
                </p>
              </div>

              <div>
                <Label htmlFor="capacidad">Capacidad</Label>
                <Input
                  id="capacidad"
                  type="number"
                  value={formData.capacidad}
                  onChange={(e) => handleInputChange('capacidad', e.target.value)}
                  placeholder="Ej: 4"
                  min="1"
                  required
                />
                <p className="text-sm text-gray-500 mt-1">
                  Número de personas que caben en la mesa
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-red-600 text-sm">{error}</p>
                </div>
              )}

              <div className="flex gap-3 pt-4">
                <Button
                  type="submit"
                  disabled={loading}
                  className="flex-1"
                >
                  {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Crear Mesa
                </Button>
                <Link href="/dashboard/mesas" className="flex-1">
                  <Button type="button" variant="outline" className="w-full">
                    Cancelar
                  </Button>
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* Información adicional */}
      <Card className="max-w-md">
        <CardHeader>
          <CardTitle>Información</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-gray-600">
          <p>• El número de mesa debe ser único</p>
          <p>• La capacidad determina cuántas personas pueden sentarse</p>
          <p>• Las mesas se crean en estado &quot;Libre&quot; por defecto</p>
          <p>• Puedes cambiar el estado y editar la información después</p>
        </CardContent>
      </Card>
    </div>
  );
}