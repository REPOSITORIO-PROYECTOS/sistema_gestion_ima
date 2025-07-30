// app/dashboard/contabilidad/page.tsx
"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useAuthStore } from "@/lib/authStore";
import { DataTable } from "@/components/ui/data-table"; // Asegúrate que la ruta a tu DataTable es correcta
import { columns } from "./libro-mayor/columns";
import type { MovimientoContable } from "@/types/contabilidad.types"; // Usamos el tipo que creamos
import { useMovimientosCajaStore } from "@/lib/useMovimientosCajaStore"; // Asegúrate que la ruta a tu store es correcta

// Componentes de la Interfaz de Usuario
import { FiltrosCaja } from "./_components/FiltrosCaja";
import { BotonFacturarLote } from "./_components/BotonFacturarLote";
import { NavegacionContabilidad } from "./_components/NavegacionContabilidad";

export default function ContabilidadPage() {
  const token = useAuthStore((state) => state.token);

  // CAMBIO: Usamos nuestro tipo específico 'MovimientoContable' en lugar de 'any[]'
  const [movimientos, setMovimientos] = useState<MovimientoContable[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const filtroActual = useMovimientosCajaStore((state) => state.filtroActual);

  // CAMBIO: Envolvemos la función en 'useCallback' para estabilizarla y
  // poder usarla como dependencia en 'useEffect' de forma segura.
  const fetchMovimientos = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/contabilidad/libro-mayor-caja", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Error al obtener los movimientos de caja desde el servidor.");
      
      const result = await res.json();
      setMovimientos(result);
    } catch (err) {
      // CAMBIO: Se tipa el error para cumplir con las reglas de ESLint.
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Ocurrió un error desconocido al cargar los datos.");
      }
    } finally {
      setLoading(false);
    }
  }, [token]); // La función solo se volverá a crear si el 'token' cambia.

  // CAMBIO: 'fetchMovimientos' ahora se incluye en el array de dependencias.
  useEffect(() => {
    fetchMovimientos();
  }, [fetchMovimientos]);

  // 'useMemo' para filtrar los datos eficientemente en el cliente.
  const movimientosFiltrados = useMemo(() => {
    if (!movimientos) return [];
    switch (filtroActual) {
      case "PENDIENTES":
        return movimientos.filter(m => m.tipo === 'VENTA' && m.venta && !m.venta.facturada);
      case "FACTURADOS":
        return movimientos.filter(m => m.tipo === 'VENTA' && m.venta && m.venta.facturada);
      case "INGRESOS":
        return movimientos.filter(m => m.tipo === 'INGRESO');
      case "EGRESOS":
        return movimientos.filter(m => m.tipo === 'EGRESO');
      default:
        return movimientos;
    }
  }, [movimientos, filtroActual]);

  // Función que se pasará al botón para recargar los datos después de una acción.
  const handleFacturacionExitosa = () => {
    fetchMovimientos();
  };

  return (
    <div className="flex flex-col p-4 gap-6">
      <div>
        <h1 className="text-3xl font-semibold">Sección de Contabilidad</h1>
        <p className="text-gray-600 mt-1">
          Revise los últimos movimientos de caja a continuación.
        </p>
      </div>
      
      <NavegacionContabilidad />
      
      <div className="flex flex-col gap-4">
        {loading ? (
          <p className="text-center p-8">Cargando datos...</p>
        ) : error ? (
          <div className="text-center p-8 text-red-600">
            <p><strong>Error al cargar los datos:</strong></p>
            <p>{error}</p>
          </div>
        ) : (
          <>
            <div className="flex justify-between items-center">
              <FiltrosCaja />
              <BotonFacturarLote onFacturacionExitosa={handleFacturacionExitosa} />
            </div>
            
            <DataTable columns={columns} data={movimientosFiltrados} />
          </>
        )}
      </div>
    </div>
  );
}