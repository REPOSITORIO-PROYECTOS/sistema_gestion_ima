import { describe, expect, it } from "vitest";
import { generarSugerenciasCodigoInterno } from "./codigoInternoSugerencias";

describe("generarSugerenciasCodigoInterno", () => {
  it("sugiere secuencial según prefijo dominante del catálogo", () => {
    const existentes = ["LOC-001", "LOC-002", "LOC-005"];
    const sugerencias = generarSugerenciasCodigoInterno("Yerba mate 500g", existentes);
    expect(sugerencias[0]).toBe("LOC-006");
  });

  it("genera prefijo desde el nombre si no hay catálogo previo", () => {
    const sugerencias = generarSugerenciasCodigoInterno("Aceite girasol 900ml", []);
    expect(sugerencias.some((s) => s.startsWith("ACE-GIR"))).toBe(true);
  });

  it("no repite códigos ya existentes", () => {
    const existentes = ["YER-MAT-001"];
    const sugerencias = generarSugerenciasCodigoInterno("Yerba mate", existentes);
    expect(sugerencias).not.toContain("YER-MAT-001");
  });
});
