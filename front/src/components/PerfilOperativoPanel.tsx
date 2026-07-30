"use client";

import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuthStore } from "@/lib/authStore";
import { seccionesEstadisticasResueltas } from "@/lib/permisos";
import type {
  PanelEstadisticasSecciones,
  PerfilOperativoResuelto,
  SeccionEstadisticasKey,
  TipoEsquemaEmpresa,
} from "@/types/perfilOperativo";
import {
  SECCIONES_ESTADISTICAS_DEFAULT,
  SECCIONES_ESTADISTICAS_LABELS,
} from "@/types/perfilOperativo";

type Plantilla = {
  id: string;
  nombre: string;
  descripcion: string;
};

type PerfilAdminResponse = {
  id_empresa: number;
  tipo_esquema: TipoEsquemaEmpresa;
  perfil_operativo_resuelto: PerfilOperativoResuelto;
  modo_especial_habilitado: boolean;
  tiene_archivo: boolean;
};

const API_BASE = "https://sistema-ima.sistemataup.online/api";

const SECCION_KEYS = Object.keys(SECCIONES_ESTADISTICAS_DEFAULT) as SeccionEstadisticasKey[];

type Props = {
  empresaId: number;
};

export function PerfilOperativoPanel({ empresaId }: Props) {
  const { token } = useAuthStore();
  const [loading, setLoading] = React.useState(true);
  const [savingSecciones, setSavingSecciones] = React.useState(false);
  const [perfilAdmin, setPerfilAdmin] = React.useState<PerfilAdminResponse | null>(null);
  const [plantillas, setPlantillas] = React.useState<Plantilla[]>([]);
  const [tipoEsquema, setTipoEsquema] = React.useState<TipoEsquemaEmpresa>("estandar");
  const [plantillaId, setPlantillaId] = React.useState("modo_especial_pos");
  const [seccionesDraft, setSeccionesDraft] = React.useState<PanelEstadisticasSecciones>(
    SECCIONES_ESTADISTICAS_DEFAULT,
  );

  const headers = React.useMemo(
    () => ({
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    }),
    [token],
  );

  const cargar = React.useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [perfilRes, plantillasRes] = await Promise.all([
        fetch(`${API_BASE}/empresas/admin/${empresaId}/perfil-operativo`, { headers }),
        fetch(`${API_BASE}/empresas/admin/plantillas-perfil`, { headers }),
      ]);
      if (!perfilRes.ok) throw new Error("No se pudo cargar el perfil operativo.");
      if (!plantillasRes.ok) throw new Error("No se pudieron cargar las plantillas.");
      const perfilData = (await perfilRes.json()) as PerfilAdminResponse;
      const plantillasData = (await plantillasRes.json()) as Plantilla[];
      setPerfilAdmin(perfilData);
      setTipoEsquema(perfilData.tipo_esquema);
      setPlantillas(plantillasData);
      setSeccionesDraft(seccionesEstadisticasResueltas(perfilData.perfil_operativo_resuelto));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al cargar perfil");
    } finally {
      setLoading(false);
    }
  }, [empresaId, headers, token]);

  React.useEffect(() => {
    cargar();
  }, [cargar]);

  const migrar = async () => {
    if (!token) return;
    try {
      const body =
        tipoEsquema === "estandar"
          ? { tipo_esquema: "estandar" }
          : { tipo_esquema: "especial", plantilla_id: plantillaId };
      const res = await fetch(`${API_BASE}/empresas/admin/${empresaId}/migrar-esquema`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Error al migrar esquema");
      }
      toast.success("Esquema migrado correctamente");
      await cargar();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al migrar");
    }
  };

  const guardarSecciones = async () => {
    if (!token) return;
    setSavingSecciones(true);
    try {
      const res = await fetch(`${API_BASE}/empresas/admin/${empresaId}/perfil-operativo`, {
        method: "PATCH",
        headers,
        body: JSON.stringify({ panel_estadisticas_secciones: seccionesDraft }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(
          typeof err.detail === "string" ? err.detail : "No se pudieron guardar las secciones",
        );
      }
      toast.success("Secciones del panel actualizadas");
      await cargar();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Error al guardar secciones");
    } finally {
      setSavingSecciones(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-muted-foreground">Cargando perfil operativo...</p>;
  }

  const resuelto = perfilAdmin?.perfil_operativo_resuelto;
  const panelOn = Boolean(resuelto?.panel_estadisticas_caja);
  const puedeEditarSecciones =
    panelOn && perfilAdmin?.tipo_esquema === "especial";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase">
          Esquema: {perfilAdmin?.tipo_esquema ?? "—"}
        </span>
        {resuelto?.plantilla_origen && (
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800">
            Plantilla: {resuelto.plantilla_origen}
          </span>
        )}
        {perfilAdmin?.tiene_archivo && (
          <span className="text-xs text-amber-700">Perfil archivado disponible</span>
        )}
      </div>

      {resuelto && (
        <ul className="grid gap-2 text-sm sm:grid-cols-2">
          <li>Modo especial: {resuelto.modo_especial ? "Sí" : "No"}</li>
          <li>Sync Sheets: {resuelto.sincronizar_google_sheets ? "Sí" : "No"}</li>
          <li>Solo comprobante: {resuelto.caja_solo_comprobante ? "Sí" : "No"}</li>
          <li>Panel estadísticas: {resuelto.panel_estadisticas_caja ? "Sí" : "No"}</li>
        </ul>
      )}

      {puedeEditarSecciones && (
        <div className="space-y-3 rounded-md border border-slate-200 p-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Secciones del panel de estadísticas
            </h3>
            <p className="text-xs text-muted-foreground">
              Checklist de bloques visibles para dueños / encargadas.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {SECCION_KEYS.map((key) => (
              <label key={key} className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={seccionesDraft[key]}
                  onCheckedChange={(checked) =>
                    setSeccionesDraft((prev) => ({
                      ...prev,
                      [key]: checked === true,
                    }))
                  }
                />
                <span>{SECCIONES_ESTADISTICAS_LABELS[key]}</span>
              </label>
            ))}
          </div>
          <Button
            type="button"
            size="sm"
            onClick={() => void guardarSecciones()}
            disabled={savingSecciones}
          >
            {savingSecciones ? "Guardando..." : "Guardar secciones"}
          </Button>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>Esquema destino</Label>
          <Select value={tipoEsquema} onValueChange={(v) => setTipoEsquema(v as TipoEsquemaEmpresa)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="estandar">Estándar (IMA clásico)</SelectItem>
              <SelectItem value="especial">Especial (POS / La Esquina)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {tipoEsquema === "especial" && (
          <div className="space-y-2">
            <Label>Plantilla</Label>
            <Select value={plantillaId} onValueChange={setPlantillaId}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {plantillas.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.nombre}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      <Button type="button" variant="secondary" onClick={migrar}>
        Migrar esquema
      </Button>
    </div>
  );
}
