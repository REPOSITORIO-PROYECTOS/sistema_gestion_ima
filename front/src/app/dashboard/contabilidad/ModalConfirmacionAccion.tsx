"use client"

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2 } from "lucide-react";
import { ReactNode } from "react";

// La interfaz ahora incluye las props opcionales para el selector
interface ModalConfirmacionProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
  
  titulo: string;
  descripcion: string;
  textoBotonConfirmar: string;
  
  children?: ReactNode;

  // Props opcionales para renderizar el selector
  mostrarSelector?: boolean;
  valorSelector?: string;
  onSelectorChange?: (value: string) => void;
  opcionesSelector?: { value: string; label: string }[];
}

export function ModalConfirmacionAccion({
  isOpen,
  onClose,
  onConfirm,
  isLoading,
  titulo,
  descripcion,
  textoBotonConfirmar,
  children,
  // Se reciben las nuevas props con valores por defecto
  mostrarSelector = false,
  valorSelector,
  onSelectorChange,
  opcionesSelector = []
}: ModalConfirmacionProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          <DialogDescription>{descripcion}</DialogDescription>
        </DialogHeader>
        
        {/* Aquí se renderiza el resumen de ítems que le pases */}
        {children}

        {/* El selector solo aparece si 'mostrarSelector' es true */}
        {mostrarSelector && (
          <div className="grid gap-4 py-4 border-t mt-4 pt-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="tipo-final" className="text-right">
                Convertir a:
              </Label>
              <Select value={valorSelector} onValueChange={onSelectorChange}>
                <SelectTrigger id="tipo-final" className="col-span-3">
                  <SelectValue placeholder="Seleccionar tipo..." />
                </SelectTrigger>
                <SelectContent>
                  {opcionesSelector.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button onClick={onConfirm} disabled={isLoading}>
            {isLoading ? <Loader2 className="animate-spin" /> : textoBotonConfirmar}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}