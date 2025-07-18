'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import ProtectedRoute from '@/components/ProtectedRoute';

// Comidas Hardcodeadas
const comidas = [
  {
    id: '1',
    nombre: 'Hamburguesa Clásica',
    descripcion: 'Pan artesanal, carne 100%, cheddar y lechuga',
    precio: 4500,
    imagen: '/images/1.webp',
  },
  {
    id: '2',
    nombre: 'Pizza Margarita',
    descripcion: 'Mozzarella, tomate, albahaca fresca',
    precio: 6000,
    imagen: '/images/5.jpg',
  },
  {
    id: '3',
    nombre: 'Papas Fritas',
    descripcion: 'Con cheddar y bacon',
    precio: 3200,
    imagen: '/images/2.webp',
  },
  {
    id: '4',
    nombre: 'Hamburguesa Clásica',
    descripcion: 'Pan artesanal, carne 100%, cheddar y lechuga',
    precio: 4500,
    imagen: '/images/3.webp',
  },
  {
    id: '5',
    nombre: 'Pizza Margarita',
    descripcion: 'Mozzarella, tomate, albahaca fresca',
    precio: 6000,
    imagen: '/images/4.webp',
  },
  {
    id: '6',
    nombre: 'Papas Fritas',
    descripcion: 'Con cheddar y bacon',
    precio: 3200,
    imagen: '/images/5.jpg',
  },
];

export default function Page() {

  const [pedido, setPedido] = useState<typeof comidas>([]);

  // Agregamos plato al pedido (si no está)
  function agregarAlPedido(plato: typeof comidas[0]) {
    setPedido((actual) => [...actual, plato]);
  }

  // Elimina plato del pedido por índice
  function eliminarDelPedido(idx: number) {
    setPedido((actual) => actual.filter((_, i) => i !== idx));
  }

  return (

    <ProtectedRoute allowedRoles={['Admin']}>

      <div className="flex h-screen gap-6">

        {/* Sección de cards */}
        <div className="flex-1 overflow-y-auto p-4">
          <h2 className="text-2xl font-bold mb-4">Carta</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {comidas.map((comida, idx) => (

              <Card
                key={idx}
                onClick={() => agregarAlPedido(comida)}
                className="relative h-72 cursor-pointer hover:scale-[1.02] transition overflow-hidden"
              >
                <Image
                  src={comida.imagen}
                  alt={comida.nombre}
                  fill
                  className="object-cover"
                />
                <div className="absolute inset-0 bg-black/40 z-0" />
                <div className="absolute inset-0 p-4 flex flex-col justify-end z-10">
                  <CardHeader className="p-0">
                    <CardTitle className="text-white">{comida.nombre}</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0 text-white text-sm">
                    <p>{comida.descripcion}</p>
                    <p className="font-bold mt-1">${comida.precio}</p>
                  </CardContent>
                </div>
              </Card>

            ))}
          </div>
        </div>

        {/* Sección Resumen */}
        <div className="w-full max-w-sm p-8 rounded-xl bg-gray-300 overflow-y-auto">
          <h3 className="text-xl font-semibold mb-4">Resumen del Pedido #002381</h3>

          {/* Si no hay pedidos.. */}
          {pedido.length === 0 && (
            <p className="text-muted-foreground">No hay platos seleccionados</p>
          )}

          {/* Si los hay, render */}
          <ul className="space-y-3">
            {pedido.map((plato, i) => (

              <li key={i} className="flex justify-between items-center bg-white rounded-md px-4 py-3 shadow">
                <span>{plato.nombre}</span>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => eliminarDelPedido(i)}
                >
                  Eliminar
                </Button>
              </li>

            ))}
          </ul>
        </div>

      </div>

    </ProtectedRoute>
  );
}