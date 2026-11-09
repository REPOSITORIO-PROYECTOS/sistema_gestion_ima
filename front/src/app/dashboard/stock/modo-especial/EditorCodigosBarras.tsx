"use client";

import { useRef, useState } from "react";
import { X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { agregarAlternativo, unirCodigos } from "./ingreso-linea";

type EditorCodigosBarrasProps = {
  codigos: string[];
  onChange: (codigos: string[]) => void;
  autoFocus?: boolean;
};

export function EditorCodigosBarras({ codigos, onChange, autoFocus = false }: EditorCodigosBarrasProps) {
  const principal = codigos[0] ?? "";
  const alternativos = codigos.slice(1);
  const [borrador, setBorrador] = useState("");
  const [aviso, setAviso] = useState("");
  const alternativoRef = useRef<HTMLInputElement>(null);

  const publicar = (siguientePrincipal: string, siguientesAlternativos: string[]) => {
    onChange(unirCodigos(siguientePrincipal, siguientesAlternativos));
  };

  const agregar = () => {
    const resultado = agregarAlternativo(principal, alternativos, borrador);
    if (!resultado.ok) {
      setAviso(resultado.motivo === "duplicado" ? "Ese código ya está en el producto." : "");
      alternativoRef.current?.focus();
      return;
    }
    setAviso("");
    setBorrador("");
    publicar(principal, resultado.alternativos);
    alternativoRef.current?.focus();
  };

  return (
    <div className="space-y-2 min-w-[14rem]">
      <Input
        aria-label="Código de barras principal"
        placeholder="Principal"
        className="h-8 font-mono text-xs"
        value={principal}
        autoFocus={autoFocus}
        onChange={(e) => {
          setAviso("");
          publicar(e.target.value, alternativos);
        }}
      />
      <div className="flex flex-wrap gap-1">
        {alternativos.map((codigo) => (
          <span
            key={codigo}
            className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 font-mono text-[11px] text-amber-950"
          >
            {codigo}
            <button
              type="button"
              aria-label={`Quitar ${codigo}`}
              className="rounded-full hover:bg-amber-200"
              onClick={() => publicar(principal, alternativos.filter((item) => item !== codigo))}
            >
              <X className="size-3" />
            </button>
          </span>
        ))}
      </div>
      <Input
        ref={alternativoRef}
        aria-label="Código de barras alternativo"
        placeholder="Alternativo + Enter"
        className="h-8 font-mono text-xs"
        value={borrador}
        onChange={(e) => {
          setAviso("");
          setBorrador(e.target.value);
        }}
        onKeyDown={(e) => {
          if (e.key !== "Enter") return;
          e.preventDefault();
          agregar();
        }}
      />
      {aviso && <p className="text-[11px] text-red-700">{aviso}</p>}
    </div>
  );
}
