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
import { Loader2, Lock, Pencil } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/lib/authStore";
import { API_CONFIG } from "@/lib/api-config";
import type { ArqueoCaja } from "./columns";

interface AccionesArqueoProps {
  arqueo: ArqueoCaja;
  onActionComplete?: () => void;
}

const aNumero = (valor: string): number => {
  const n = parseFloat(valor);
  return Number.isFinite(n) ? n : 0;
};

export function AccionesArqueo({ arqueo, onActionComplete }: AccionesArqueoProps) {
  const token = useAuthStore((state) => state.token);
  const rol = useAuthStore((state) => state.usuario?.rol?.nombre);
  const esAdmin = rol === "Admin";

  const [modalCerrar, setModalCerrar] = useState(false);
  const [modalEditar, setModalEditar] = useState(false);
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

  if (!esAdmin) return null;

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
    // Construimos el payload solo con los campos completados.
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

  return (
    <div className="flex gap-2">
      {arqueo.estado === "ABIERTA" && (
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
              automáticamente en el servidor.
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
    </div>
  );
}
