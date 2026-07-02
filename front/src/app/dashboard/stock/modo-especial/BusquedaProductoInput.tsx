"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api-client";
import { API_CONFIG } from "@/lib/api-config";
import { useAuthStore } from "@/lib/authStore";

const LIMITE_BUSQUEDA = 40;

type ProductoMatch = {
  id: number;
  codigo_interno: string;
  descripcion: string;
  stock_actual: number;
};

type ArticuloBusqueda = {
  id: number;
  codigo_interno?: string;
  descripcion: string;
  stock_actual?: number;
};

interface BusquedaProductoInputProps {
  codigoInterno: string;
  descripcion: string;
  onChange: (codigoInterno: string, descripcion: string) => void;
  placeholder?: string;
}

export function BusquedaProductoInput({
  codigoInterno,
  descripcion,
  onChange,
  placeholder = "Nombre o código de barras",
}: BusquedaProductoInputProps) {
  const token = useAuthStore((s) => s.token);
  const [texto, setTexto] = useState(descripcion || codigoInterno);
  const [matches, setMatches] = useState<ProductoMatch[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const [justSelected, setJustSelected] = useState(Boolean(codigoInterno && descripcion));
  const debounceRef = useRef<number | undefined>(undefined);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const mapResultados = (data: ArticuloBusqueda[]): ProductoMatch[] =>
    data
      .filter((a) => a.codigo_interno)
      .map((a) => ({
        id: a.id,
        codigo_interno: a.codigo_interno as string,
        descripcion: a.descripcion,
        stock_actual: a.stock_actual ?? 0,
      }));

  useEffect(() => {
    if (!codigoInterno) {
      setTexto("");
      setJustSelected(false);
      return;
    }
    if (descripcion) {
      setTexto(descripcion);
      setJustSelected(true);
    }
  }, [codigoInterno, descripcion]);

  useEffect(() => {
    if (highlightIndex < 0 || !listRef.current) return;
    const item = listRef.current.querySelector<HTMLElement>(
      `[data-result-index="${highlightIndex}"]`,
    );
    item?.scrollIntoView({ block: "nearest" });
  }, [highlightIndex]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
        setHighlightIndex(-1);
      }
    };
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const seleccionar = useCallback(
    (prod: ProductoMatch) => {
      onChange(prod.codigo_interno, prod.descripcion);
      setTexto(prod.descripcion);
      setJustSelected(true);
      setOpen(false);
      setHighlightIndex(-1);
    },
    [onChange],
  );

  const buscarPorCodigoBarras = useCallback(
    async (codigo: string) => {
      if (!token) return false;
      const res = await fetch(
        `${API_CONFIG.BASE_URL}/articulos/codigos/buscar/${encodeURIComponent(codigo)}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) return false;
      const data = (await res.json()) as ArticuloBusqueda;
      if (!data.codigo_interno) return false;
      seleccionar({
        id: data.id,
        codigo_interno: data.codigo_interno,
        descripcion: data.descripcion,
        stock_actual: data.stock_actual ?? 0,
      });
      return true;
    },
    [seleccionar, token],
  );

  useEffect(() => {
    const q = texto.trim();
    window.clearTimeout(debounceRef.current);

    if (!q) {
      setMatches([]);
      setHighlightIndex(-1);
      if (!justSelected) setOpen(false);
      return;
    }

    if (justSelected && q === descripcion) return;

    const isLikelyBarcode = /^\d{8,}$/.test(q);
    const debounceDelay = isLikelyBarcode ? 50 : 280;

    debounceRef.current = window.setTimeout(async () => {
      setLoading(true);
      try {
        const resp = await api.articulos.buscar(q, LIMITE_BUSQUEDA);
        const data = (resp.success ? (resp.data as ArticuloBusqueda[]) : []) || [];
        const mapped = mapResultados(data);
        setMatches(mapped);
        setHighlightIndex(mapped.length > 0 ? 0 : -1);
        if (mapped.length > 0) {
          setOpen(true);
          setJustSelected(false);
        }
      } finally {
        setLoading(false);
      }
    }, debounceDelay);

    return () => window.clearTimeout(debounceRef.current);
  }, [texto, justSelected, descripcion]);

  const onKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
      setHighlightIndex(-1);
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setJustSelected(false);
      if (!open || matches.length === 0) {
        const q = texto.trim();
        setLoading(true);
        try {
          const resp = await api.articulos.buscar(q, LIMITE_BUSQUEDA);
          const data = (resp.success ? (resp.data as ArticuloBusqueda[]) : []) || [];
          const mapped = mapResultados(data);
          setMatches(mapped);
          setHighlightIndex(mapped.length > 0 ? 0 : -1);
          if (mapped.length > 0) setOpen(true);
        } finally {
          setLoading(false);
        }
        return;
      }
      setHighlightIndex((prev) => Math.min(prev + 1, matches.length - 1));
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (open && matches.length > 0) {
        setHighlightIndex((prev) => Math.max(prev - 1, 0));
      }
      return;
    }

    if (e.key === "Enter" && texto.trim()) {
      e.preventDefault();
      const q = texto.trim();
      if (open && highlightIndex >= 0 && highlightIndex < matches.length && !/^\d{8,}$/.test(q)) {
        seleccionar(matches[highlightIndex]);
        return;
      }
      if (justSelected && codigoInterno && q === descripcion) return;
      const encontrado = await buscarPorCodigoBarras(q);
      if (!encontrado && matches.length === 1) {
        seleccionar(matches[0]);
      }
    }
  };

  return (
    <div className="relative min-w-[12rem]">
      <Input
        ref={inputRef}
        type="text"
        value={texto}
        onChange={(e) => {
          const newValue = e.target.value;
          setTexto(newValue);
          if (codigoInterno && newValue !== descripcion) {
            setJustSelected(false);
            onChange("", "");
          }
        }}
        onKeyDown={onKeyDown}
        onFocus={() => {
          if (texto.trim() && matches.length > 0 && !justSelected) {
            setOpen(true);
          }
        }}
        placeholder={placeholder}
        autoComplete="off"
        className="min-w-[12rem]"
      />

      {open && (
        <div
          ref={dropdownRef}
          className="absolute z-[100] w-full mt-1 bg-white border rounded-lg shadow-lg flex flex-col max-h-48"
          onWheel={(e) => e.stopPropagation()}
        >
          <div className="px-2 py-1 text-xs text-muted-foreground border-b shrink-0">
            {loading
              ? "Buscando..."
              : matches.length > 0
                ? `${matches.length} resultado${matches.length === 1 ? "" : "s"}`
                : texto.trim()
                  ? "Sin coincidencias"
                  : "Escribí para buscar"}
          </div>
          <ul ref={listRef} className="overflow-y-auto flex-1 py-1" role="listbox">
            {!loading && matches.length === 0 && (
              <li className="py-3 text-center text-xs text-muted-foreground px-2">
                {texto.trim()
                  ? `No se encontró "${texto}". Probá con el código de barras.`
                  : "Escribí nombre o escaneá código."}
              </li>
            )}
            {matches.map((prod, index) => {
              const activo = index === highlightIndex;
              return (
                <li key={prod.id} role="option" aria-selected={activo}>
                  <button
                    type="button"
                    data-result-index={index}
                    onMouseEnter={() => setHighlightIndex(index)}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => seleccionar(prod)}
                    className={`w-full text-left px-2 py-2 flex items-center justify-between gap-2 text-sm border-b last:border-b-0 ${
                      activo ? "bg-accent" : "hover:bg-muted/50"
                    }`}
                  >
                    <span className="font-medium truncate flex-1">{prod.descripcion}</span>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {prod.codigo_interno}
                      {prod.stock_actual > 0 && ` · stk ${prod.stock_actual}`}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
