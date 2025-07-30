"use client";

import { useEffect, useState } from "react";
import { DataTable } from "./data-table";
import { columns } from "./columns";
import type { Cliente } from "./columns";
import { useAuthStore } from "@/lib/authStore";

function ClientesPage() {
  const [data, setData] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((state) => state.token);

  // GET Clientes
  useEffect(() => {
    const fetchClientes = async () => {
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/clientes/obtener-todos", {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        });

        if (!res.ok) {
          throw new Error("Error al obtener clientes");
        }

        const data = await res.json();
        const clientesFiltrados = data.filter((cliente: Cliente) => cliente);
        setData(clientesFiltrados);

      } catch (error) {
        console.error("Error al traer clientes:", error);

      } finally {
        setLoading(false);
      }
    };

    fetchClientes();
  }, [token]);

  return (
    <div className="p-4">
      {loading ? (
        <p className="text-center text-gray-500">Cargando clientes...</p>
      ) : (
        <DataTable columns={columns} data={data} />
      )}
    </div>
  );
}

export default ClientesPage;