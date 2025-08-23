"use client";

import { useEffect, useState, useCallback } from "react";
import { DataTable } from "./data-table";
import { columns } from "./columns"; 
import type { Proveedor } from "./columns";
import { useAuthStore } from "@/lib/authStore";

// El nombre de la función ahora es más convencional para una página
export default function ProveedoresPage() {
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
      if (!res.ok) throw new Error("Error al obtener proveedores");
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

  return (
    <div className="p-4 md:p-6">
      <h1 className="text-2xl font-bold mb-4">Gestión de Proveedores</h1>
      {loading ? (
        <p className="text-center text-muted-foreground">Cargando proveedores...</p>
      ) : (
        // La DataTable ya no necesita la prop onActionComplete
        <DataTable columns={columns} data={data} />
      )}
    </div>
  );
}