"use client";

import { useEffect, useState } from "react";
import { DataTable } from "./data-table";
import { columns, ProductoAPI } from "./columns";

export default function Page() {
    
  const [productos, setProductos] = useState<ProductoAPI[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProductos = async () => {
      try {
        const res = await fetch("https://sistema-ima.sistemataup.online/api/articulos/obtener_todos");
        const data: ProductoAPI[] = await res.json();
        setProductos(data);
      } catch (err) {
        console.error("❌ Error al obtener productos:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchProductos();
  }, []);

  if (loading) return <p className="text-center py-10">Cargando productos...</p>;

  return <DataTable columns={columns} data={productos} />;
}