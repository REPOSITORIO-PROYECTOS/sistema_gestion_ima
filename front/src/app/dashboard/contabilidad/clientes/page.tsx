"use client";

import { useEffect, useState } from "react";
import { DataTable } from "./data-table";
import { columns, Cliente } from "./columns";

async function getClientes(): Promise<Cliente[]> {
  const res = await fetch("https://sistema-ima.sistemataup.online/api/clientes/obtener-todos");
  const data = await res.json();
  return data.filter((cliente: Cliente) => cliente);
}

function ClientesPage() {
  const [clientes, setClientes] = useState<Cliente[]>([]);

  useEffect(() => {
    getClientes()
      .then((data) => {
        setClientes(data);
        console.log("Clientes obtenidos:", data);
      })
      .catch((err) => console.error("❌ Error al obtener clientes:", err));
  }, []);

  return <DataTable columns={columns} data={clientes} />;
}

export default ClientesPage;