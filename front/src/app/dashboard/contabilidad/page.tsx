"use client";

import { useEffect, useState } from "react";
import { DataTable } from "./data-table";
import { columns } from "./columns";
import { MovimientoAPI } from "./columns";
import { useAuthStore } from "@/lib/authStore";

export default function ContabilidadPage() {

  const [data, setData] = useState<MovimientoAPI[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((state) => state.token);

  // GET Movimientos
  useEffect(() => {
    const fetchMovimientos = async () => {
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/caja/movimientos/todos", {
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error("Error al obtener los movimientos");
        const json = await res.json();
        setData(json);

        console.log(json)

      } catch (err) {
        console.error("Error:", err);

      } finally {
        setLoading(false);
      }
    };

    fetchMovimientos();
  }, [token]);

  return (
    <div className="flex flex-col p-4 gap-6">
      <div>
        <h1 className="text-3xl font-semibold">Sección de Contabilidad</h1>
        <p className="text-gray-600 mt-1">Historial de movimientos.</p>
      </div>

      {loading ? (
        <p>Cargando movimientos...</p>
      ) : (
        <DataTable columns={columns} data={data} />
      )}
    </div>
  );
}