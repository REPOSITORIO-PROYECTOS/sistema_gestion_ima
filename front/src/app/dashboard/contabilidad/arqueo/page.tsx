"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { DataTable } from "./data-table";
import { columns } from "./columns";
import type { ArqueoCaja } from "./columns";

export default function ArqueoCajaPage() {
  const token = useAuthStore((state) => state.token);
  const [data, setData] = useState<ArqueoCaja[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // GET Arqueos
  useEffect(() => {
    if (!token) return;

    const fetchData = async () => {
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/caja/arqueos", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error("Error al obtener los arqueos");

        const result = await res.json();

        // Concatenamos las listas de abiertas y cerradas
        const combinados: ArqueoCaja[] = [
          ...result.cajas_abiertas,
          ...result.arqueos_cerrados,
        ];

        setData(combinados);
      } catch (err) {
        console.error(err);
        setError("No se pudo obtener la lista de arqueos");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [token]);

  if (loading) return <p className="text-center">Cargando datos...</p>;
  if (error) return <p className="text-center text-red-600">{error}</p>;

  return (
    <div>
      <DataTable columns={columns} data={data} />
    </div>
  );
}