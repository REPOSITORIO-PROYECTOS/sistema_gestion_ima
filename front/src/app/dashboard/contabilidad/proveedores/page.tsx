"use client";

import { useEffect, useState, useCallback } from "react";
import { DataTable } from "./data-table"; // Asegúrate que la ruta sea correcta
// ==========================================================
// === CORRECCIÓN: Importamos la CONSTANTE 'columns', no una función ===
// ==========================================================
import { columns } from "./columns"; 
import type { Proveedor } from "./columns";
import { useAuthStore } from "@/lib/authStore";

function Proveedores() {

  const [data, setData] = useState<Proveedor[]>([]);
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();
  
  const fetchProveedores = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch("https://sistema-ima.sistemataup.online/api/proveedores/obtener-todos", {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        throw new Error("Error al obtener proveedores");
      }

      const resData = await res.json();
      setData(resData);

    } catch (error) {
      console.error("Error al traer proveedores:", error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchProveedores();
  }, [fetchProveedores]);

  // Ya no necesitamos llamar a getColumns. Simplemente usamos la constante importada.

  return (
    <div className="p-4">
      <h1 className="text-3xl font-bold mb-4">Gestión de Proveedores</h1>
      {loading ? (
        <p className="text-center text-gray-500">Cargando proveedores...</p>
      ) : (
        // =====================================================================
        // === CORRECCIÓN: Pasamos la prop 'onActionComplete' a DataTable ===
        // =====================================================================
        // DataTable se encargará de pasarla a la metadata de la tabla.
        <DataTable 
          columns={columns} 
          data={data} 
          onActionComplete={fetchProveedores} 
        />
      )}
    </div>
  );
}

export default Proveedores;