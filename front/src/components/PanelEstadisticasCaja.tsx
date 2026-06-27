"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { API_CONFIG } from "@/lib/api-config";
import { formatDateArgentina } from "@/utils/formatDate";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, RefreshCw, Wallet, Receipt, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface CajaAbiertaPanelItem {
  id_sesion: number;
  fecha_apertura: string;
  usuario_apertura: string;
  saldo_inicial: number;
  cantidad_movimientos: number;
  cantidad_ventas: number;
  total_ventas: number;
}

interface PanelEstadisticasData {
  cajas_abiertas: CajaAbiertaPanelItem[];
  resumen: {
    total_cajas_abiertas: number;
    total_ventas: number;
    total_movimientos: number;
  };
}

interface PanelEstadisticasCajaProps {
  compact?: boolean;
  refreshIntervalMs?: number;
}

function formatearMoneda(valor: number): string {
  return valor.toLocaleString("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
  });
}

export default function PanelEstadisticasCaja({
  compact = false,
  refreshIntervalMs = 30000,
}: PanelEstadisticasCajaProps) {
  const token = useAuthStore((state) => state.token);
  const [data, setData] = useState<PanelEstadisticasData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchPanel = useCallback(
    async (silent = false) => {
      if (!token) return;
      if (!silent) setLoading(true);
      else setRefreshing(true);

      try {
        const res = await fetch(`${API_CONFIG.BASE_URL}/caja/panel-estadisticas`, {
          headers: { Authorization: `Bearer ${token}` },
          cache: "no-store",
        });

        if (res.status === 403) {
          setError("No tiene permisos para ver el panel de estadísticas.");
          setData(null);
          return;
        }

        if (!res.ok) throw new Error("Error al cargar estadísticas de caja");

        const json: PanelEstadisticasData = await res.json();
        setData(json);
        setError(null);
        setLastUpdated(new Date());
      } catch (err) {
        console.error(err);
        setError("No se pudo cargar el panel de estadísticas.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [token],
  );

  useEffect(() => {
    void fetchPanel();
    const interval = setInterval(() => void fetchPanel(true), refreshIntervalMs);
    return () => clearInterval(interval);
  }, [fetchPanel, refreshIntervalMs]);

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-8 text-gray-600">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Cargando estadísticas de caja...</span>
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

  const { cajas_abiertas, resumen } = data;

  return (
    <div className="w-full space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-green-950">
            {compact ? "Cajas abiertas" : "Panel de estadísticas — Cajas abiertas"}
          </h2>
          {lastUpdated && (
            <p className="text-sm text-gray-500">
              Actualizado: {lastUpdated.toLocaleTimeString("es-AR", { hour12: false })}
            </p>
          )}
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void fetchPanel(true)}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Actualizar
        </Button>
      </div>

      {/* Resumen general */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="bg-emerald-50 border-emerald-200">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2 text-emerald-800">
              <Wallet className="h-4 w-4" />
              Cajas abiertas
            </CardDescription>
            <CardTitle className="text-3xl text-emerald-950">
              {resumen.total_cajas_abiertas}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card className="bg-blue-50 border-blue-200">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2 text-blue-800">
              <Receipt className="h-4 w-4" />
              Total ventas
            </CardDescription>
            <CardTitle className="text-2xl text-blue-950">
              {formatearMoneda(resumen.total_ventas)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card className="bg-amber-50 border-amber-200">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-2 text-amber-800">
              <Activity className="h-4 w-4" />
              Movimientos
            </CardDescription>
            <CardTitle className="text-3xl text-amber-950">
              {resumen.total_movimientos}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Detalle por caja */}
      {cajas_abiertas.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-gray-600">
            No hay cajas abiertas en este momento.
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {cajas_abiertas.map((caja) => (
            <Card key={caja.id_sesion} className="border-green-200">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-lg text-green-950">
                      {caja.usuario_apertura}
                    </CardTitle>
                    <CardDescription>
                      Sesión #{caja.id_sesion} · Apertura {formatDateArgentina(caja.fecha_apertura)}
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="bg-green-100 text-green-800 border-green-300">
                    Abierta
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <dt className="text-gray-500">Saldo inicial</dt>
                  <dd className="font-semibold text-right">{formatearMoneda(caja.saldo_inicial)}</dd>
                  <dt className="text-gray-500">Ventas registradas</dt>
                  <dd className="font-semibold text-right">{caja.cantidad_ventas}</dd>
                  <dt className="text-gray-500">Total vendido</dt>
                  <dd className="font-semibold text-right text-emerald-700">
                    {formatearMoneda(caja.total_ventas)}
                  </dd>
                  <dt className="text-gray-500">Movimientos</dt>
                  <dd className="font-semibold text-right">{caja.cantidad_movimientos}</dd>
                </dl>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
