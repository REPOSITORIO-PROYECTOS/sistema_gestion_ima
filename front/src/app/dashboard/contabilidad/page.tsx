"use client";

import { useEffect, useState, useCallback } from "react";
import { DataTable } from "./data-table";
import { columns } from "./columns";
import { MovimientoAPI } from "./columns";
import { useAuthStore } from "@/lib/authStore";
import ProtectedRoute from "@/components/ProtectedRoute";

export default function ContabilidadPage() {
  const [data, setData] = useState<MovimientoAPI[]>([]);
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();

  /**
   * Función para obtener los movimientos de la API.
   * Se envuelve en `useCallback` para memorizarla y evitar que se
   * recree en cada renderizado, optimizando el rendimiento y cumpliendo
   * con las reglas de los hooks de React.
   * Solo se volverá a crear si la dependencia `token` cambia.
   */
  const fetchData = useCallback(async () => {
    // Pre-condición: No intentar hacer la llamada si no hay token.
    if (!token) {
      setLoading(false); // Dejamos de cargar si no podemos hacer nada
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/caja/movimientos/todos", {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        // Si la respuesta no es exitosa, lanzamos un error para que lo capture el 'catch'.
        throw new Error(`Error ${res.status}: Fallo al obtener los movimientos`);
      }
      
      const json = await res.json();
      setData(json);

    } catch (err) {
      console.error("Error al obtener los datos:", err);
      // Aquí podrías añadir una notificación al usuario (ej. con toast.error).
      setData([]); // En caso de error, es bueno limpiar los datos viejos.
    } finally {
      // Este bloque se ejecuta siempre, tanto si hubo éxito como si hubo error.
      setLoading(false);
    }
  }, [token]); // El array de dependencias de useCallback.

  /**
   * `useEffect` para ejecutar la carga de datos.
   * Ahora depende de la función `fetchData` memoizada.
   * Esto asegura que se llame a la función la primera vez que se monta el
   * componente y cada vez que `fetchData` se actualice (es decir, cuando cambie el token).
   */
  useEffect(() => {
    fetchData();
  }, [fetchData]); // La dependencia es la propia función, como recomienda ESLint.

  return (
    <ProtectedRoute allowedRoles={["Admin", "Soporte"]}>
      <div className="container mx-auto flex flex-col gap-6 py-4">
        <h1 className="text-2xl font-bold text-green-950">Movimientos de Caja</h1>
        
        {loading ? (
          <div className="flex justify-center items-center h-64">
            <p className="text-gray-500">Cargando movimientos...</p>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={data}
            token={token}
            onActionComplete={fetchData}
          />
        )}
      </div>
    </ProtectedRoute>
  );
}