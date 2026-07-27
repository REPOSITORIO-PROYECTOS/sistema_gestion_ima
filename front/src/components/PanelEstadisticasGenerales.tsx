"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { API_CONFIG } from "@/lib/api-config";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Loader2,
  RefreshCw,
  ShoppingCart,
  TrendingUp,
  PackageX,
  Store,
} from "lucide-react";

interface EstablecimientoStat {
  id_empresa: number;
  nombre: string;
  cantidad_ventas: number;
  total_ventas: number;
  ticket_promedio: number;
}

interface ProductoTop {
  id_articulo: number;
  descripcion: string;
  cantidad_vendida: number;
  monto_total: number;
}

interface StockBajo {
  id_articulo: number;
  descripcion: string;
  stock_actual: number;
  stock_minimo: number;
  id_empresa: number;
  nombre_empresa: string;
}

interface EstadisticasGeneralesData {
  periodo: string;
  desde: string;
  hasta: string;
  cantidad_ventas: number;
  total_ventas: number;
  ticket_promedio: number;
  por_establecimiento: EstablecimientoStat[];
  top_productos: ProductoTop[];
  stock_bajo: StockBajo[];
}

function formatearMoneda(valor: number): string {
  return valor.toLocaleString("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
  });
}

interface PanelEstadisticasGeneralesProps {
  compact?: boolean;
}

export default function PanelEstadisticasGenerales({
  compact = false,
}: PanelEstadisticasGeneralesProps) {
  const token = useAuthStore((state) => state.token);
  const [data, setData] = useState<EstadisticasGeneralesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(
    async (silent = false) => {
      if (!token) return;
      if (!silent) setLoading(true);
      else setRefreshing(true);

      try {
        const res = await fetch(
          `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CAJA_ESTADISTICAS_GENERALES}`,
          {
            headers: { Authorization: `Bearer ${token}` },
            cache: "no-store",
          },
        );

        if (res.status === 403) {
          setError("No tiene permisos para ver las estadísticas generales.");
          setData(null);
          return;
        }
        if (!res.ok) throw new Error("Error al cargar estadísticas generales");

        const json: EstadisticasGeneralesData = await res.json();
        setData(json);
        setError(null);
      } catch (err) {
        console.error(err);
        setError("No se pudieron cargar las estadísticas generales.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [token],
  );

  useEffect(() => {
    void fetchStats();
  }, [fetchStats]);

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-6 text-gray-600">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Cargando estadísticas del mes...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="pt-6 text-red-700">{error}</CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const mostrarEstablecimientos = data.por_establecimiento.length > 1;

  return (
    <div className="w-full space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-green-950">
            {compact ? "Resumen del mes" : "Estadísticas generales — Mes en curso"}
          </h2>
          <p className="text-sm text-gray-500">Período {data.periodo}</p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void fetchStats(true)}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Actualizar
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="bg-slate-50 border-slate-200">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2 text-slate-700">
              <ShoppingCart className="h-4 w-4" />
              Ventas del mes
            </CardDescription>
            <CardTitle className="text-2xl text-slate-950">
              {formatearMoneda(data.total_ventas)}
            </CardTitle>
            <p className="text-sm text-gray-500">{data.cantidad_ventas} tickets</p>
          </CardHeader>
        </Card>
        <Card className="bg-indigo-50 border-indigo-200">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2 text-indigo-800">
              <TrendingUp className="h-4 w-4" />
              Ticket promedio
            </CardDescription>
            <CardTitle className="text-2xl text-indigo-950">
              {formatearMoneda(data.ticket_promedio)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card className="bg-rose-50 border-rose-200">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2 text-rose-800">
              <PackageX className="h-4 w-4" />
              Productos con stock bajo
            </CardDescription>
            <CardTitle className="text-3xl text-rose-950">
              {data.stock_bajo.length}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {mostrarEstablecimientos && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-green-950 flex items-center gap-2">
            <Store className="h-4 w-4" />
            Por establecimiento
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.por_establecimiento.map((est) => (
              <Card key={est.id_empresa} className="border-green-100">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base text-green-950">{est.nombre}</CardTitle>
                  <CardDescription>
                    {est.cantidad_ventas} ventas · prom. {formatearMoneda(est.ticket_promedio)}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-xl font-semibold text-emerald-800">
                    {formatearMoneda(est.total_ventas)}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Productos más vendidos</CardTitle>
            <CardDescription>Top 10 del mes por monto</CardDescription>
          </CardHeader>
          <CardContent>
            {data.top_productos.length === 0 ? (
              <p className="text-sm text-gray-500">Sin ventas en el período.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {data.top_productos.map((p, idx) => (
                  <li
                    key={p.id_articulo}
                    className="flex items-start justify-between gap-3 border-b border-gray-100 pb-2 last:border-0"
                  >
                    <span className="text-gray-800">
                      <span className="text-gray-400 mr-2">{idx + 1}.</span>
                      {p.descripcion}
                      <span className="block text-xs text-gray-500">
                        {p.cantidad_vendida.toLocaleString("es-AR")} u.
                      </span>
                    </span>
                    <span className="font-semibold whitespace-nowrap">
                      {formatearMoneda(p.monto_total)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Stock bajo / faltante</CardTitle>
            <CardDescription>Bajo el mínimo configurado</CardDescription>
          </CardHeader>
          <CardContent>
            {data.stock_bajo.length === 0 ? (
              <p className="text-sm text-gray-500">No hay productos bajo el mínimo.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {data.stock_bajo.map((p) => (
                  <li
                    key={`${p.id_empresa}-${p.id_articulo}`}
                    className="flex items-start justify-between gap-3 border-b border-gray-100 pb-2 last:border-0"
                  >
                    <span>
                      <span className="text-gray-800">{p.descripcion}</span>
                      {mostrarEstablecimientos && (
                        <span className="block text-xs text-gray-500">{p.nombre_empresa}</span>
                      )}
                    </span>
                    <span className="text-rose-700 font-semibold whitespace-nowrap">
                      {p.stock_actual} / {p.stock_minimo}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
