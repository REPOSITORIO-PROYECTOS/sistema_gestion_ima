"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuthStore } from "@/lib/authStore";
import { API_CONFIG } from "@/lib/api-config";
import { usePerfilEmpresa } from "@/hooks/usePerfilEmpresa";
import { seccionEstadisticasVisible } from "@/lib/permisos";
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
  AlertTriangle,
  Users,
  CreditCard,
  Tags,
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

interface StockItem {
  id_articulo: number;
  descripcion: string;
  stock_actual: number;
  stock_minimo: number;
  id_empresa: number;
  nombre_empresa: string;
}

interface KpisPeriodo {
  venta_hoy: number;
  venta_ayer: number;
  venta_mes: number;
  venta_mes_anterior: number;
  pct_vs_mes_anterior: number | null;
  tickets_hoy: number;
  tickets_mes: number;
  ticket_promedio_hoy: number;
  ticket_promedio_mes: number;
}

interface AlertasStock {
  sin_stock: StockItem[];
  stock_bajo: StockItem[];
  cantidad_sin_stock: number;
  cantidad_stock_bajo: number;
}

interface DiferenciaCaja {
  id_sesion: number;
  fecha_cierre: string | null;
  usuario_cierre: string | null;
  diferencia: number;
  id_empresa: number;
  nombre_empresa: string;
}

interface CategoriaTop {
  categoria: string;
  cantidad_vendida: number;
  monto_total: number;
}

interface VendedorRanking {
  id_usuario: number;
  nombre_usuario: string;
  cantidad_ventas: number;
  total_ventas: number;
}

interface MedioPago {
  metodo_pago: string;
  cantidad: number;
  monto_total: number;
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
  stock_bajo: StockItem[];
  kpis?: KpisPeriodo | null;
  alertas_stock?: AlertasStock | null;
  alertas_diferencias_caja?: DiferenciaCaja[];
  top_categorias?: CategoriaTop[];
  ranking_vendedores?: VendedorRanking[];
  medios_pago?: MedioPago[];
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
  const { perfil } = usePerfilEmpresa();
  const [data, setData] = useState<EstadisticasGeneralesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const showKpis = seccionEstadisticasVisible(perfil, "kpis_periodo");
  const showStock = seccionEstadisticasVisible(perfil, "alertas_stock");
  const showDiff = seccionEstadisticasVisible(perfil, "alertas_diferencias_caja");
  const showProductos = seccionEstadisticasVisible(perfil, "top_productos");
  const showCategorias = seccionEstadisticasVisible(perfil, "top_categorias");
  const showRanking = seccionEstadisticasVisible(perfil, "ranking_vendedores");
  const showMedios = seccionEstadisticasVisible(perfil, "medios_pago");
  const showEstablecimientos = seccionEstadisticasVisible(perfil, "por_establecimiento");

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

  const kpis = data.kpis;
  const alertasStock = data.alertas_stock;
  const diferencias = data.alertas_diferencias_caja ?? [];
  const topCategorias = data.top_categorias ?? [];
  const ranking = data.ranking_vendedores ?? [];
  const medios = data.medios_pago ?? [];
  const mostrarEstablecimientos =
    showEstablecimientos && data.por_establecimiento.length > 1;

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

      {showKpis && kpis && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-emerald-50 border-emerald-200">
            <CardHeader className="pb-2">
              <CardDescription className="text-emerald-800">Venta hoy</CardDescription>
              <CardTitle className="text-2xl text-emerald-950">
                {formatearMoneda(kpis.venta_hoy)}
              </CardTitle>
              <p className="text-sm text-gray-500">{kpis.tickets_hoy} tickets</p>
            </CardHeader>
          </Card>
          <Card className="bg-slate-50 border-slate-200">
            <CardHeader className="pb-2">
              <CardDescription className="text-slate-700">Venta ayer</CardDescription>
              <CardTitle className="text-2xl text-slate-950">
                {formatearMoneda(kpis.venta_ayer)}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card className="bg-indigo-50 border-indigo-200">
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2 text-indigo-800">
                <ShoppingCart className="h-4 w-4" />
                Venta del mes
              </CardDescription>
              <CardTitle className="text-2xl text-indigo-950">
                {formatearMoneda(kpis.venta_mes)}
              </CardTitle>
              <p className="text-sm text-gray-500">{kpis.tickets_mes} tickets</p>
            </CardHeader>
          </Card>
          <Card className="bg-amber-50 border-amber-200">
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2 text-amber-800">
                <TrendingUp className="h-4 w-4" />
                Vs mes anterior
              </CardDescription>
              <CardTitle className="text-2xl text-amber-950">
                {kpis.pct_vs_mes_anterior == null
                  ? "—"
                  : `${kpis.pct_vs_mes_anterior > 0 ? "+" : ""}${kpis.pct_vs_mes_anterior}%`}
              </CardTitle>
              <p className="text-sm text-gray-500">
                Ant. {formatearMoneda(kpis.venta_mes_anterior)}
              </p>
            </CardHeader>
          </Card>
          <Card className="bg-blue-50 border-blue-200 sm:col-span-2 lg:col-span-2">
            <CardHeader className="pb-2">
              <CardDescription className="text-blue-800">Ticket promedio</CardDescription>
              <CardTitle className="text-2xl text-blue-950">
                Hoy {formatearMoneda(kpis.ticket_promedio_hoy)} · Mes{" "}
                {formatearMoneda(kpis.ticket_promedio_mes)}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {!showKpis && (
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
          {showStock && (
            <Card className="bg-rose-50 border-rose-200">
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-2 text-rose-800">
                  <PackageX className="h-4 w-4" />
                  Alertas de stock
                </CardDescription>
                <CardTitle className="text-3xl text-rose-950">
                  {(alertasStock?.cantidad_sin_stock ?? 0) +
                    (alertasStock?.cantidad_stock_bajo ?? data.stock_bajo.length)}
                </CardTitle>
              </CardHeader>
            </Card>
          )}
        </div>
      )}

      {(showStock || showDiff) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {showStock && (
            <Card className="border-rose-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <PackageX className="h-4 w-4 text-rose-700" />
                  Alertas de stock
                </CardTitle>
                <CardDescription>
                  Sin stock: {alertasStock?.cantidad_sin_stock ?? 0} · Bajo mínimo:{" "}
                  {alertasStock?.cantidad_stock_bajo ?? data.stock_bajo.length}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-xs font-semibold uppercase text-rose-800 mb-2">Sin stock</p>
                  {(alertasStock?.sin_stock ?? []).length === 0 ? (
                    <p className="text-sm text-gray-500">Sin productos en cero.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {(alertasStock?.sin_stock ?? []).map((p) => (
                        <li
                          key={`sin-${p.id_empresa}-${p.id_articulo}`}
                          className="flex justify-between gap-3 border-b border-gray-100 pb-2"
                        >
                          <span>
                            {p.descripcion}
                            {mostrarEstablecimientos && (
                              <span className="block text-xs text-gray-500">{p.nombre_empresa}</span>
                            )}
                          </span>
                          <span className="font-semibold text-rose-700">{p.stock_actual}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase text-amber-800 mb-2">Stock bajo</p>
                  {(alertasStock?.stock_bajo ?? data.stock_bajo).length === 0 ? (
                    <p className="text-sm text-gray-500">No hay productos bajo el mínimo.</p>
                  ) : (
                    <ul className="space-y-2 text-sm">
                      {(alertasStock?.stock_bajo ?? data.stock_bajo).map((p) => (
                        <li
                          key={`bajo-${p.id_empresa}-${p.id_articulo}`}
                          className="flex justify-between gap-3 border-b border-gray-100 pb-2"
                        >
                          <span>
                            {p.descripcion}
                            {mostrarEstablecimientos && (
                              <span className="block text-xs text-gray-500">{p.nombre_empresa}</span>
                            )}
                          </span>
                          <span className="font-semibold text-amber-700 whitespace-nowrap">
                            {p.stock_actual} / {p.stock_minimo}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {showDiff && (
            <Card className="border-amber-200">
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-700" />
                  Diferencias de caja
                </CardTitle>
                <CardDescription>Últimas sesiones cerradas con diferencia ≠ 0</CardDescription>
              </CardHeader>
              <CardContent>
                {diferencias.length === 0 ? (
                  <p className="text-sm text-gray-500">Sin diferencias registradas.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {diferencias.map((d) => (
                      <li
                        key={d.id_sesion}
                        className="flex justify-between gap-3 border-b border-gray-100 pb-2"
                      >
                        <span>
                          Sesión #{d.id_sesion}
                          {d.usuario_cierre ? ` · ${d.usuario_cierre}` : ""}
                          {mostrarEstablecimientos && (
                            <span className="block text-xs text-gray-500">{d.nombre_empresa}</span>
                          )}
                        </span>
                        <span
                          className={`font-semibold whitespace-nowrap ${
                            d.diferencia < 0 ? "text-rose-700" : "text-amber-700"
                          }`}
                        >
                          {formatearMoneda(d.diferencia)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

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
        {showProductos && (
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
        )}

        {showCategorias && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Tags className="h-4 w-4" />
                Categorías más vendidas
              </CardTitle>
              <CardDescription>Top del mes por monto</CardDescription>
            </CardHeader>
            <CardContent>
              {topCategorias.length === 0 ? (
                <p className="text-sm text-gray-500">Sin datos de categorías.</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {topCategorias.map((c, idx) => (
                    <li
                      key={`${c.categoria}-${idx}`}
                      className="flex justify-between gap-3 border-b border-gray-100 pb-2"
                    >
                      <span>
                        <span className="text-gray-400 mr-2">{idx + 1}.</span>
                        {c.categoria}
                      </span>
                      <span className="font-semibold">{formatearMoneda(c.monto_total)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        )}

        {showRanking && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Users className="h-4 w-4" />
                Ranking vendedoras
              </CardTitle>
              <CardDescription>Ventas del mes</CardDescription>
            </CardHeader>
            <CardContent>
              {ranking.length === 0 ? (
                <p className="text-sm text-gray-500">Sin ventas por usuario.</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {ranking.map((v, idx) => (
                    <li
                      key={v.id_usuario}
                      className="flex justify-between gap-3 border-b border-gray-100 pb-2"
                    >
                      <span>
                        <span className="text-gray-400 mr-2">{idx + 1}.</span>
                        {v.nombre_usuario}
                        <span className="block text-xs text-gray-500">
                          {v.cantidad_ventas} tickets
                        </span>
                      </span>
                      <span className="font-semibold">{formatearMoneda(v.total_ventas)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        )}

        {showMedios && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <CreditCard className="h-4 w-4" />
                Medios de pago
              </CardTitle>
              <CardDescription>Mes en curso</CardDescription>
            </CardHeader>
            <CardContent>
              {medios.length === 0 ? (
                <p className="text-sm text-gray-500">Sin movimientos de venta.</p>
              ) : (
                <ul className="space-y-2 text-sm">
                  {medios.map((m) => (
                    <li
                      key={m.metodo_pago}
                      className="flex justify-between gap-3 border-b border-gray-100 pb-2"
                    >
                      <span>
                        {m.metodo_pago}
                        <span className="block text-xs text-gray-500">{m.cantidad} mov.</span>
                      </span>
                      <span className="font-semibold">{formatearMoneda(m.monto_total)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
