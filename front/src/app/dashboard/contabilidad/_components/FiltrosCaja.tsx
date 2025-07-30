'use client';
import { useMovimientosCajaStore } from '@/lib/useMovimientosCajaStore';

// Definimos el tipo aquí para no depender del archivo de tipos
type FiltroTipo = "TODOS" | "PENDIENTES" | "FACTURADOS" | "INGRESOS" | "EGRESOS";

export function FiltrosCaja() {
  const { filtroActual, setFiltro } = useMovimientosCajaStore();
  // CAMBIO: Le damos un tipo explícito al array
  const filtros: FiltroTipo[] = ["TODOS", "PENDIENTES", "FACTURADOS", "INGRESOS", "EGRESOS"];
  return (
    <div className="flex space-x-2">
      {filtros.map((filtro) => (
        <button key={filtro} onClick={() => setFiltro(filtro)} className={`px-3 py-1.5 text-sm rounded-md ${filtroActual === filtro ? 'bg-blue-600 text-white' : 'bg-gray-200 hover:bg-gray-300'}`}>
          {filtro.charAt(0) + filtro.slice(1).toLowerCase()}
        </button>
      ))}
    </div>
  );
}