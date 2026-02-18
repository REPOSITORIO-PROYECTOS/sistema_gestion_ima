"use client";

import { useEffect, useState } from "react";
import { DataTable } from "./data-table";
import { columns, ProductoAPI } from "./columns";
import { fetchAllArticulos } from "./api";
import { useAuthStore } from "@/lib/authStore";
import ProtectedRoute from "@/components/ProtectedRoute";

export default function StockPage() {

  const [productos, setProductos] = useState<ProductoAPI[]>([]);
  const [loading, setLoading] = useState(true);
  const token = useAuthStore((state) => state.token);

  // GET Productos para tabla Stock
  useEffect(() => {
    const fetchProductos = async () => {
      try {
        const data = await fetchAllArticulos(token);
        setProductos(data);
      } catch (err) {
        console.error("❌ Error al obtener productos:", err);

      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchProductos();
    } else {
      setLoading(false);
    }
  }, [token]);

  if (loading) return <p className="text-center py-10">Cargando productos...</p>;

  return (
    <ProtectedRoute allowedRoles={["Admin", "Soporte"]}>
      <DataTable
        key={productos.length}
        columns={columns}
        data={productos}
        loading={loading}
        onProductosActualizados={(nuevos) => setProductos(nuevos)}
      />
    </ProtectedRoute>
  )
}