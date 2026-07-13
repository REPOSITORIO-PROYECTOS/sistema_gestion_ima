"use client";

import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuthStore } from "@/lib/authStore";
import type { PerfilOperativoResuelto, TipoEsquemaEmpresa } from "@/types/perfilOperativo";

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

type Props = {
  empresaId: number;
};

export function PerfilOperativoPanel({ empresaId }: Props) {
  const { token } = useAuthStore();
  const [loading, setLoading] = React.useState(true);
  const [perfilAdmin, setPerfilAdmin] = React.useState<PerfilAdminResponse | null>(null);
  const [plantillas, setPlantillas] = React.useState<Plantilla[]>([]);
  const [tipoEsquema, setTipoEsquema] = React.useState<TipoEsquemaEmpresa>("estandar");
  const [plantillaId, setPlantillaId] = React.useState("modo_especial_pos");

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

  if (loading) {
    return <p className="text-sm text-muted-foreground">Cargando perfil operativo...</p>;
  }

  const resuelto = perfilAdmin?.perfil_operativo_resuelto;

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
