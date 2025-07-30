'use client';
import { useMovimientosCajaStore } from '@/lib/useMovimientosCajaStore';
import { useAuthStore } from '@/lib/authStore';
import React, { useState } from 'react';

export function BotonFacturarLote({ onFacturacionExitosa }: { onFacturacionExitosa: () => void; }) {
  const token = useAuthStore((state) => state.token);
  const { seleccionados, resetSeleccion } = useMovimientosCajaStore();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleFacturar = async () => {
    if (!token || seleccionados.length === 0) return;
    if (confirm(`¿Deseas facturar ${seleccionados.length} movimientos a Consumidor Final?`)) {
      setIsSubmitting(true);
      try {
        await fetch("https://sistema-ima.sistemataup.online/api/comprobantes/facturar-lote", {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ ids_movimientos: seleccionados, id_cliente_final: null })
        });
        alert('Lote facturado con éxito!');
        resetSeleccion();
        onFacturacionExitosa();
      } catch (error) {
        // CAMBIO: Tipamos el error
        if (error instanceof Error) {
          alert(`Error: ${error.message}`);
        } else {
          alert('Ocurrió un error desconocido al facturar.');
        }
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  return (
    <button onClick={handleFacturar} disabled={seleccionados.length === 0 || isSubmitting} className="bg-green-600 text-white px-4 py-2 text-sm rounded-md disabled:bg-gray-400">
      {isSubmitting ? 'Procesando...' : `Facturar Selección (${seleccionados.length})`}
    </button>
  );
}