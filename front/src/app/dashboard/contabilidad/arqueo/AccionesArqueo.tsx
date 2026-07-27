"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Lock, Pencil, CheckCircle2, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/authStore";
import { API_CONFIG } from "@/lib/api-config";
import type { ArqueoCaja } from "./columns";

interface AccionesArqueoProps {
  arqueo: ArqueoCaja;
  onActionComplete?: () => void;
}

const ROLES_SUPERVISOR = new Set(["Admin", "Gerente", "Encargada", "Soporte"]);

const aNumero = (valor: string): number => {
  const n = parseFloat(valor);
  return Number.isFinite(n) ? n : 0;
};

export function AccionesArqueo({ arqueo, onActionComplete }: AccionesArqueoProps) {
  const token = useAuthStore((state) => state.token);
  const rol =
    useAuthStore((state) => state.usuario?.rol?.nombre) ??
    useAuthStore((state) => state.role?.nombre);
  const esAdmin = rol === "Admin" || rol === "Soporte";
  const esSupervisor = Boolean(rol && ROLES_SUPERVISOR.has(rol));

  const [modalCerrar, setModalCerrar] = useState(false);
  const [modalEditar, setModalEditar] = useState(false);
  const [modalRevisar, setModalRevisar] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Estado modal Cerrar
  const [efectivo, setEfectivo] = useState("");
  const [transferencias, setTransferencias] = useState("");
  const [bancario, setBancario] = useState("");

  // Estado modal Editar
  const [editSaldoInicial, setEditSaldoInicial] = useState(String(arqueo.saldo_inicial ?? ""));
  const [editEfectivo, setEditEfectivo] = useState(
    arqueo.saldo_final_efectivo != null ? String(arqueo.saldo_final_efectivo) : "",
  );
  const [editTransferencias, setEditTransferencias] = useState(
    arqueo.saldo_final_transferencias != null ? String(arqueo.saldo_final_transferencias) : "",
  );
  const [editBancario, setEditBancario] = useState(
    arqueo.saldo_final_bancario != null ? String(arqueo.saldo_final_bancario) : "",
  );
  const [editDeclarado, setEditDeclarado] = useState(
    arqueo.saldo_final_declarado != null ? String(arqueo.saldo_final_declarado) : "",
  );

  const [notaRevision, setNotaRevision] = useState(arqueo.nota_revision ?? "");

  if (!esSupervisor) return null;

  const handleCerrarCaja = async () => {
    if (!token) {
      toast.error("No se encontró el token.");
      return;
    }
    const efectivoNum = aNumero(efectivo);
    const transferenciasNum = aNumero(transferencias);
    const bancarioNum = aNumero(bancario);
    const declarado = efectivoNum + transferenciasNum + bancarioNum;

    try {
      setIsLoading(true);
      const res = await fetch(
        `${API_CONFIG.BASE_URL}/caja/admin/cerrar-por-id/${arqueo.id_sesion}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            saldo_final_declarado: declarado,
            saldo_final_efectivo: efectivoNum,
            saldo_final_transferencias: transferenciasNum,
            saldo_final_bancario: bancarioNum,
          }),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "No se pudo cerrar la caja");
      }
      toast.success("Caja cerrada correctamente por un administrador.");
      setModalCerrar(false);
      onActionComplete?.();
    } catch (error) {
      if (error instanceof Error) toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditarSaldos = async () => {
    if (!token) {
      toast.error("No se encontró el token.");
      return;
    }
    const payload: Record<string, number> = {};
    if (editSaldoInicial.trim() !== "") payload.saldo_inicial = aNumero(editSaldoInicial);
    if (editDeclarado.trim() !== "") payload.saldo_final_declarado = aNumero(editDeclarado);
    if (editEfectivo.trim() !== "") payload.saldo_final_efectivo = aNumero(editEfectivo);
    if (editTransferencias.trim() !== "")
      payload.saldo_final_transferencias = aNumero(editTransferencias);
    if (editBancario.trim() !== "") payload.saldo_final_bancario = aNumero(editBancario);

    if (Object.keys(payload).length === 0) {
      toast.info("No hay cambios para guardar.");
      return;
    }

    try {
      setIsLoading(true);
      const res = await fetch(
        `${API_CONFIG.BASE_URL}/caja/admin/sesion/${arqueo.id_sesion}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "No se pudieron guardar los cambios");
      }
      toast.success("Saldos de la caja actualizados correctamente.");
      setModalEditar(false);
      onActionComplete?.();
    } catch (error) {
      if (error instanceof Error) toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRevisar = async (marcar: boolean) => {
    if (!token) {
      toast.error("No se encontró el token.");
      return;
    }

    try {
      setIsLoading(true);
      const res = await fetch(
        `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CAJA_REVISAR_SESION(arqueo.id_sesion)}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            revisado: marcar,
            nota_revision: marcar ? notaRevision.trim() || null : null,
          }),
        },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "No se pudo actualizar la revisión");
      }
      toast.success(
        marcar
          ? "Arqueo marcado como revisado. Diferencia tenida en cuenta."
          : "Revisión desmarcada. El arqueo vuelve a pendiente.",
      );
      setModalRevisar(false);
      onActionComplete?.();
    } catch (error) {
      if (error instanceof Error) toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {esAdmin && arqueo.estado === "ABIERTA" && (
        <Button
          variant="outline"
          size="sm"
          className="cursor-pointer"
          onClick={() => setModalCerrar(true)}
          title="Cerrar caja (Admin)"
        >
          <Lock className="h-4 w-4 mr-1" />
          Cerrar
        </Button>
      )}

      {esAdmin && (
        <Button
          variant="outline"
          size="sm"
          className="cursor-pointer"
          onClick={() => setModalEditar(true)}
          title="Editar saldos (Admin)"
        >
          <Pencil className="h-4 w-4 mr-1" />
          Editar
        </Button>
      )}

      {arqueo.estado === "CERRADA" && !arqueo.revisado && (
        <Button
          variant="outline"
          size="sm"
          className="cursor-pointer border-emerald-300 text-emerald-800 hover:bg-emerald-50"
          onClick={() => {
            setNotaRevision(arqueo.nota_revision ?? "");
            setModalRevisar(true);
          }}
          title="Marcar arqueo como revisado"
        >
          <CheckCircle2 className="h-4 w-4 mr-1" />
          Revisar
        </Button>
      )}

      {arqueo.estado === "CERRADA" && arqueo.revisado && (
        <Button
          variant="ghost"
          size="sm"
          className="cursor-pointer text-gray-600"
          onClick={() => void handleRevisar(false)}
          disabled={isLoading}
          title="Quitar marca de revisado"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin mr-1" />
          ) : (
            <RotateCcw className="h-4 w-4 mr-1" />
          )}
          Quitar revisión
        </Button>
      )}

      {/* Modal Cerrar Caja */}
      <Dialog open={modalCerrar} onOpenChange={setModalCerrar}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Cerrar caja (Sesión #{arqueo.id_sesion})</DialogTitle>
            <DialogDescription>
              Ingrese los montos declarados. Caja abierta por {arqueo.usuario_apertura}.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-1">
              <Label>Efectivo</Label>
              <Input
                type="number"
                value={efectivo}
                onChange={(e) => setEfectivo(e.target.value)}
                placeholder="0.00"
              />
            </div>
            <div className="grid gap-1">
              <Label>Transferencias</Label>
              <Input
                type="number"
                value={transferencias}
                onChange={(e) => setTransferencias(e.target.value)}
                placeholder="0.00"
              />
            </div>
            <div className="grid gap-1">
              <Label>POS / Bancario</Label>
              <Input
                type="number"
                value={bancario}
                onChange={(e) => setBancario(e.target.value)}
                placeholder="0.00"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="destructive" onClick={handleCerrarCaja} disabled={isLoading}>
              {isLoading && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
              Cerrar caja
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Editar Saldos */}
      <Dialog open={modalEditar} onOpenChange={setModalEditar}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Editar saldos (Sesión #{arqueo.id_sesion})</DialogTitle>
            <DialogDescription>
              Modifique los saldos. El saldo calculado y la diferencia se recalculan
              automáticamente en el servidor. Si el arqueo estaba revisado, la revisión
              se anula.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="grid gap-1">
              <Label>Saldo inicial</Label>
              <Input
                type="number"
                value={editSaldoInicial}
                onChange={(e) => setEditSaldoInicial(e.target.value)}
              />
            </div>
            <div className="grid gap-1">
              <Label>Saldo declarado (total)</Label>
              <Input
                type="number"
                value={editDeclarado}
                onChange={(e) => setEditDeclarado(e.target.value)}
                placeholder="Solo cajas cerradas"
              />
            </div>
            <div className="grid gap-1">
              <Label>Efectivo</Label>
              <Input
                type="number"
                value={editEfectivo}
                onChange={(e) => setEditEfectivo(e.target.value)}
              />
            </div>
            <div className="grid gap-1">
              <Label>Transferencias</Label>
              <Input
                type="number"
                value={editTransferencias}
                onChange={(e) => setEditTransferencias(e.target.value)}
              />
            </div>
            <div className="grid gap-1">
              <Label>POS / Bancario</Label>
              <Input
                type="number"
                value={editBancario}
                onChange={(e) => setEditBancario(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button onClick={handleEditarSaldos} disabled={isLoading}>
              {isLoading && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
              Guardar cambios
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Revisar */}
      <Dialog open={modalRevisar} onOpenChange={setModalRevisar}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Revisar arqueo (Sesión #{arqueo.id_sesion})</DialogTitle>
            <DialogDescription>
              Confirme que revisó este cierre y tuvo en cuenta la diferencia.
              No se modifican los saldos.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-3 py-2 text-sm">
            <div className="flex justify-between gap-4">
              <span className="text-gray-500">Diferencia</span>
              <span
                className={
                  arqueo.diferencia === 0 || arqueo.diferencia == null
                    ? "font-semibold text-green-700"
                    : "font-semibold text-red-700"
                }
              >
                {arqueo.diferencia == null
                  ? "—"
                  : new Intl.NumberFormat("es-AR", {
                      style: "currency",
                      currency: "ARS",
                    }).format(arqueo.diferencia)}
              </span>
            </div>
            <div className="grid gap-1">
              <Label htmlFor="nota-revision">Nota (opcional)</Label>
              <Textarea
                id="nota-revision"
                value={notaRevision}
                onChange={(e) => setNotaRevision(e.target.value)}
                placeholder="Ej: diferencia por vuelto mal registrado, ya conversado con cajero"
                rows={3}
                maxLength={500}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              className="bg-emerald-700 hover:bg-emerald-800"
              onClick={() => void handleRevisar(true)}
              disabled={isLoading}
            >
              {isLoading && <Loader2 className="animate-spin mr-2 h-4 w-4" />}
              Marcar revisado
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
