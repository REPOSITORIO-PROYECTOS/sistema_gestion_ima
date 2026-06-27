"use client"

import { LegacyRef, useCallback, useEffect, useRef, useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ChevronsDown, RefreshCw, Lock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api-client"

const LIMITE_BUSQUEDA = 40
const LIMITE_LISTADO = 100

type Producto = {
  id: string;
  nombre: string;
  precio_venta: number;
  venta_negocio: number;
  stock_actual: number;
  unidad_venta: string;
  precio_manual?: boolean;
};

type MinimalArticulo = {
  id: number;
  descripcion: string;
  precio_venta: number;
  venta_negocio?: number;
  stock_actual?: number;
  unidad_venta?: string;
  precio_manual?: boolean;
};

interface SeccionProductoProps {
  inputRef: LegacyRef<HTMLInputElement>;
  codigo: string;
  setCodigoEscaneado: (codigo: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  productoSeleccionado: Producto | null;
  setProductoSeleccionado: (producto: Producto | null) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  tipoClienteSeleccionadoId: string;
  popoverOpen: boolean;
  setPopoverOpen: (open: boolean) => void;
  productoEscaneado: Producto | null;
  cantidadEscaneada: number;
  setCantidadEscaneada: (cantidad: number) => void;
  handleAgregarDesdePopover: () => void;
  persistirProducto: boolean;
  setPersistirProducto: (v: boolean) => void;
  onRefrescarProductos: () => void | Promise<void>;
  catalogoResetTick?: number;
  onProductoConfirmado?: () => void;
}

export function SeccionProducto(props: SeccionProductoProps) {
  const {
    inputRef,
    codigo,
    setCodigoEscaneado,
    handleKeyDown,
    productoSeleccionado,
    setProductoSeleccionado,
    popoverOpen,
    setPopoverOpen,
    persistirProducto,
    setPersistirProducto,
    onRefrescarProductos,
    onProductoConfirmado,
  } = props;

  const [matches, setMatches] = useState<Producto[]>([]);
  const [loading, setLoading] = useState(false);
  const [justSelected, setJustSelected] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const debounceRef = useRef<number | undefined>(undefined);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const mapBusqueda = (data: MinimalArticulo[]): Producto[] =>
    data.map((a) => ({
      id: String(a.id),
      nombre: a.descripcion,
      precio_venta: a.precio_venta,
      venta_negocio: a.venta_negocio ?? a.precio_venta,
      stock_actual: a.stock_actual ?? 0,
      unidad_venta: a.unidad_venta ?? "unidad",
      precio_manual: a.precio_manual ?? false,
    }));

  const seleccionarProducto = useCallback(
    (prod: Producto) => {
      setProductoSeleccionado(prod);
      setCodigoEscaneado(prod.nombre);
      setJustSelected(true);
      setPopoverOpen(false);
      setHighlightIndex(-1);
      onProductoConfirmado?.();
      setTimeout(() => {
        if (inputRef && "current" in inputRef && inputRef.current) {
          inputRef.current.focus();
        }
      }, 50);
    },
    [inputRef, onProductoConfirmado, setCodigoEscaneado, setPopoverOpen, setProductoSeleccionado],
  );

  const buscarEnServidor = useCallback(
    async (termino: string, limit: number) => {
      setLoading(true);
      try {
        const resp = await api.articulos.buscar(termino, limit);
        const data = (resp.success ? (resp.data as MinimalArticulo[]) : []) || [];
        const mapped = mapBusqueda(data);
        setMatches(mapped);
        setHighlightIndex(mapped.length > 0 ? 0 : -1);
        if (mapped.length > 0) {
          setPopoverOpen(true);
          setJustSelected(false);
        }
      } finally {
        setLoading(false);
      }
    },
    [setPopoverOpen],
  );

  useEffect(() => {
    if (highlightIndex < 0 || !listRef.current) return;
    const item = listRef.current.querySelector<HTMLElement>(
      `[data-result-index="${highlightIndex}"]`,
    );
    item?.scrollIntoView({ block: "nearest" });
  }, [highlightIndex]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        const inputElement = inputRef && "current" in inputRef ? inputRef.current : null;
        if (inputElement && !inputElement.contains(event.target as Node)) {
          setPopoverOpen(false);
          setHighlightIndex(-1);
        }
      }
    };

    if (popoverOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [popoverOpen, inputRef, setPopoverOpen]);

  useEffect(() => {
    const q = (codigo || "").trim();

    window.clearTimeout(debounceRef.current);

    const isLikelyBarcode = q && /^\d{8,}$/.test(q);
    const debounceDelay = isLikelyBarcode ? 50 : 280;

    debounceRef.current = window.setTimeout(async () => {
      if (!q) {
        setMatches([]);
        setHighlightIndex(-1);
        if (!justSelected) {
          setPopoverOpen(false);
        }
        return;
      }

      setLoading(true);
      try {
        const resp = await api.articulos.buscar(q, LIMITE_BUSQUEDA);
        const data = (resp.success ? (resp.data as MinimalArticulo[]) : []) || [];
        const mapped = mapBusqueda(data);
        setMatches(mapped);
        setHighlightIndex(mapped.length > 0 ? 0 : -1);
        if (mapped.length > 0) {
          setPopoverOpen(true);
          setJustSelected(false);
        }
      } finally {
        setLoading(false);
      }
    }, debounceDelay);

    return () => window.clearTimeout(debounceRef.current);
  }, [codigo, justSelected, setPopoverOpen]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      setPopoverOpen(false);
      setHighlightIndex(-1);
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setJustSelected(false);

      if (!popoverOpen || matches.length === 0) {
        void buscarEnServidor(codigo.trim(), codigo.trim() ? LIMITE_BUSQUEDA : LIMITE_LISTADO);
        return;
      }

      setHighlightIndex((prev) => Math.min(prev + 1, matches.length - 1));
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (popoverOpen && matches.length > 0) {
        setHighlightIndex((prev) => Math.max(prev - 1, 0));
      }
      return;
    }

    if (e.key === "Enter" && codigo.trim()) {
      e.preventDefault();
      if (
        popoverOpen &&
        highlightIndex >= 0 &&
        highlightIndex < matches.length &&
        !/^\d{8,}$/.test(codigo.trim())
      ) {
        seleccionarProducto(matches[highlightIndex]);
        return;
      }
      if (
        productoSeleccionado &&
        codigo.trim() === productoSeleccionado.nombre &&
        !popoverOpen
      ) {
        onProductoConfirmado?.();
        return;
      }
      handleKeyDown(e);
    }
  };

  const precioMostrar = (prod: Producto) =>
    props.tipoClienteSeleccionadoId === "0" ? prod.precio_venta : prod.venta_negocio;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-4 items-start">
        <Label
          htmlFor="codigo-barras"
          className="text-lg font-semibold text-green-900 md:text-right md:pt-2"
        >
          Escáner / Código
        </Label>
        <div className="md:col-span-2">
          <div className="flex gap-2">
            <div className="relative w-full">
              <Input
                id="codigo-barras"
                ref={inputRef}
                type="text"
                value={codigo}
                onChange={(e) => {
                  const newValue = e.target.value;
                  setCodigoEscaneado(newValue);
                  if (productoSeleccionado && newValue !== productoSeleccionado.nombre) {
                    setJustSelected(false);
                    setProductoSeleccionado(null);
                  }
                }}
                onKeyDown={onKeyDown}
                onFocus={() => {
                  if (codigo.trim() && matches.length > 0 && !justSelected) {
                    setPopoverOpen(true);
                  }
                }}
                className="border w-full font-semibold text-base min-h-12 touch-manipulation"
                autoFocus
                enterKeyHint="next"
                placeholder="Escribí nombre o escaneá código de barras"
                autoComplete="off"
              />

              {popoverOpen && (
                <div
                  ref={dropdownRef}
                  className="absolute z-50 w-full mt-1 bg-white border-2 border-green-600 rounded-lg shadow-xl flex flex-col max-h-[min(24rem,55vh)]"
                  onWheel={(e) => e.stopPropagation()}
                >
                  {productoSeleccionado && (
                    <div className="px-3 py-2 text-sm flex items-center justify-between border-b bg-green-50 shrink-0 rounded-t-lg">
                      <span className="font-semibold text-green-900 text-xs truncate pr-2">
                        Seleccionado: {productoSeleccionado.nombre}
                      </span>
                      <span className="text-green-700 font-bold text-xs shrink-0">
                        ${productoSeleccionado.precio_venta.toFixed(2)}
                      </span>
                    </div>
                  )}

                  <div className="px-3 py-1.5 text-xs text-gray-500 border-b bg-gray-50 shrink-0 flex justify-between gap-2">
                    <span>
                      {loading
                        ? "Buscando..."
                        : matches.length > 0
                          ? `${matches.length} resultado${matches.length === 1 ? "" : "s"} — ↑↓ para moverte, scroll para ver más`
                          : codigo.trim()
                            ? "Sin coincidencias"
                            : "Listado inicial"}
                    </span>
                  </div>

                  <ul
                    ref={listRef}
                    className="overflow-y-auto overflow-x-hidden flex-1 overscroll-contain py-1"
                    role="listbox"
                    aria-label="Resultados de búsqueda"
                  >
                    {!loading && matches.length === 0 && (
                      <li className="py-6 text-center text-sm text-gray-500 px-3">
                        {codigo.trim()
                          ? `No se encontró "${codigo}". Probá con menos letras o el código de barras.`
                          : "Escribí para buscar o usá ↓ para ver productos."}
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
                            onClick={() => seleccionarProducto(prod)}
                            className={`w-full text-left px-3 py-2.5 flex items-center justify-between gap-3 border-b border-gray-100 last:border-b-0 transition-colors ${
                              activo
                                ? "bg-green-100 text-green-950"
                                : "hover:bg-green-50 text-gray-900"
                            }`}
                          >
                            <span className="font-medium text-sm leading-snug flex-1 min-w-0 break-words">
                              {prod.nombre}
                            </span>
                            <span className="flex items-center gap-2 shrink-0 text-sm">
                              <span className="font-semibold text-green-800">
                                ${precioMostrar(prod).toFixed(0)}
                              </span>
                              {prod.stock_actual > 0 && (
                                <span className="text-xs bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-medium">
                                  stk {prod.stock_actual}
                                </span>
                              )}
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>

            <Button
              type="button"
              variant="outline"
              className="shrink-0"
              onClick={() => void buscarEnServidor("", LIMITE_LISTADO)}
              aria-label="Ver listado de productos"
              title="Ver hasta 100 productos (scroll en la lista)"
            >
              <ChevronsDown className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="outline"
              className="shrink-0"
              onClick={() => {
                void onRefrescarProductos();
                void buscarEnServidor(
                  codigo.trim(),
                  codigo.trim() ? LIMITE_BUSQUEDA : LIMITE_LISTADO,
                );
              }}
              aria-label="Actualizar stock de productos en carrito"
              title="Actualizar stock"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant={persistirProducto ? "default" : "outline"}
              className="shrink-0"
              onClick={() => setPersistirProducto(!persistirProducto)}
              aria-label="Bloquear producto seleccionado"
            >
              <Lock className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
