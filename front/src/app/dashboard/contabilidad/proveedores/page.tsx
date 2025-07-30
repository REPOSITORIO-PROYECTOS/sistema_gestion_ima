"use client";

import { useEffect, useState } from "react";
import { DataTable } from "./data-table";
import { columns } from "./columns";
import type { Proveedor } from "./columns";
import { useAuthStore } from "@/lib/authStore";

function Proveedores() {

  const [data, setData] = useState<Proveedor[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((state) => state.token);
  
  // GET Proveedores
  useEffect(() => {

    const fetchProveedores = async () => {
      
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

        const data = await res.json();
        console.log(data)
        setData(data);

      } catch (error) {
        console.error("Error al traer proveedores:", error);

      } finally {
        setLoading(false);
      }
    };

    fetchProveedores();
  }, [token]);

  return (
    <div className="p-4">
      {loading ? (
        <p className="text-center text-gray-500">Cargando proveedores...</p>
      ) : (
        <DataTable columns={columns} data={data} />
      )}
    </div>
  );
}

export default Proveedores;