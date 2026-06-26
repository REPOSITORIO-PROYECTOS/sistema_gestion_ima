"use client";

import { useEffect, useState } from "react";
import { DataTable } from "./data-table";
import { columns, ProductoAPI } from "./columns";
import { fetchAllArticulos } from "./api";
import { useAuthStore } from "@/lib/authStore";
import { useEmpresaStore } from "@/lib/empresaStore";
import { API_CONFIG } from "@/lib/api-config";
import ProtectedRoute from "@/components/ProtectedRoute";
import { ModoEspecialView } from "./modo-especial/ModoEspecialView";

export default function StockPage() {
  const [productos, setProductos] = useState<ProductoAPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [modoEspecial, setModoEspecial] = useState<boolean | null>(null);
  const token = useAuthStore((state) => state.token);
  const empresa = useEmpresaStore((state) => state.empresa);

  useEffect(() => {
    const resolverModoEspecial = async () => {
      if (empresa?.modo_especial_habilitado !== undefined) {
        setModoEspecial(Boolean(empresa.modo_especial_habilitado));
        return;
      }
      if (!token) {
        setModoEspecial(false);
        return;
      }
      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}/configuracion/mi-empresa`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setModoEspecial(Boolean(data.modo_especial_habilitado));
          const current = useEmpresaStore.getState().empresa;
          useEmpresaStore.getState().setEmpresa({
            id_empresa: data.id_empresa,
            color_principal: data.color_principal ?? current?.color_principal ?? "bg-sky-800",
            ...(current ?? {}),
            ...data,
          });
        } else {
          setModoEspecial(false);
        }
      } catch {
        setModoEspecial(false);
      }
    };
    resolverModoEspecial();
  }, [token, empresa]);

  useEffect(() => {
    if (modoEspecial !== false) return;

    const fetchProductos = async () => {
      try {
        if (!token) return;
        const data = await fetchAllArticulos(token as string);
        setProductos(data);
      } catch (err) {
        console.error("Error al obtener productos:", err);
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchProductos();
    } else {
      setLoading(false);
    }
  }, [token, modoEspecial]);

  if (modoEspecial === null) {
    return <p className="text-center py-10">Cargando configuración...</p>;
  }

  return (
    <ProtectedRoute allowedRoles={["Admin", "Gerente", "Encargada", "Soporte"]}>
      {modoEspecial ? (
        <ModoEspecialView />
      ) : loading ? (
        <p className="text-center py-10">Cargando productos...</p>
      ) : (
        <DataTable
          key={productos.length}
          columns={columns}
          data={productos}
          loading={loading}
          onProductosActualizados={(nuevos) => setProductos(nuevos)}
        />
      )}
    </ProtectedRoute>
  );
}
