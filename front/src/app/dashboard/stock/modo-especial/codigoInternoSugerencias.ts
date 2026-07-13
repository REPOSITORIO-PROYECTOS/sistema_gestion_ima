const SOLO_ALFANUM = /[^a-zA-Z0-9]/g;

function sinAcentos(texto: string): string {
  return texto.normalize("NFD").replace(/\p{M}/gu, "");
}

function palabrasSignificativas(descripcion: string): string[] {
  return descripcion
    .trim()
    .split(/\s+/)
    .map((p) => sinAcentos(p).replace(SOLO_ALFANUM, ""))
    .filter((p) => p.length > 0);
}

function prefijoDesdeNombre(descripcion: string): string {
  const palabras = palabrasSignificativas(descripcion);
  if (palabras.length === 0) return "PROD";
  if (palabras.length === 1) {
    return palabras[0].slice(0, 6).toUpperCase();
  }
  const a = palabras[0].slice(0, 3).toUpperCase();
  const b = palabras[1].slice(0, 3).toUpperCase();
  return `${a}-${b}`;
}

function detectarPrefijoDominante(codigosExistentes: string[]): string | null {
  const conteo = new Map<string, number>();
  for (const codigo of codigosExistentes) {
    const match = codigo.match(/^([A-Za-z]+)-\d+$/);
    if (!match) continue;
    const prefijo = match[1].toUpperCase();
    conteo.set(prefijo, (conteo.get(prefijo) ?? 0) + 1);
  }
  if (conteo.size === 0) return null;
  let mejor: string | null = null;
  let max = 0;
  for (const [prefijo, cantidad] of conteo) {
    if (cantidad > max) {
      max = cantidad;
      mejor = prefijo;
    }
  }
  return mejor;
}

function maximoSecuencial(codigosExistentes: string[], prefijo: string): number {
  const prefijoUpper = prefijo.toUpperCase();
  let max = 0;
  for (const codigo of codigosExistentes) {
    const match = codigo.match(/^([A-Za-z]+)-(\d+)$/);
    if (!match) continue;
    if (match[1].toUpperCase() !== prefijoUpper) continue;
    const num = parseInt(match[2], 10);
    if (!Number.isNaN(num) && num > max) max = num;
  }
  return max;
}

function codigoSecuencial(prefijo: string, numero: number, pad = 3): string {
  return `${prefijo.toUpperCase()}-${String(numero).padStart(pad, "0")}`;
}

function slugCompacto(descripcion: string): string {
  const palabras = palabrasSignificativas(descripcion);
  if (palabras.length === 0) return "";
  const unidas = palabras
    .slice(0, 3)
    .map((p) => p.slice(0, 4).toUpperCase())
    .join("");
  const numeros = descripcion.match(/\d+/g)?.join("") ?? "";
  return (unidas + numeros).slice(0, 12).toUpperCase();
}

export function generarSugerenciasCodigoInterno(
  descripcion: string,
  codigosExistentes: string[],
  codigoActual?: string,
): string[] {
  const ocupados = new Set(
    codigosExistentes.map((c) => c.toUpperCase()).filter((c) => c !== codigoActual?.toUpperCase()),
  );
  const sugerencias: string[] = [];
  const agregar = (codigo: string) => {
    const normalizado = codigo.trim().toUpperCase();
    if (!normalizado || ocupados.has(normalizado) || sugerencias.includes(normalizado)) return;
    sugerencias.push(normalizado);
  };

  const prefijoCatalogo = detectarPrefijoDominante(codigosExistentes);
  const prefijoNombre = prefijoDesdeNombre(descripcion);

  if (prefijoCatalogo) {
    const siguiente = maximoSecuencial(codigosExistentes, prefijoCatalogo) + 1;
    agregar(codigoSecuencial(prefijoCatalogo, siguiente));
  }

  if (prefijoNombre) {
    const siguienteNombre = maximoSecuencial(codigosExistentes, prefijoNombre) + 1;
    agregar(codigoSecuencial(prefijoNombre, siguienteNombre));
    if (!prefijoCatalogo) {
      agregar(codigoSecuencial(prefijoNombre, siguienteNombre + 1));
    }
  }

  const compacto = slugCompacto(descripcion);
  if (compacto) agregar(compacto);

  if (sugerencias.length === 0 && descripcion.trim()) {
    agregar(codigoSecuencial("PROD", codigosExistentes.length + 1));
  }

  return sugerencias.slice(0, 4);
}
