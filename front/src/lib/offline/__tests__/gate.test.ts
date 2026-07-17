import { isCacheDegradadoActivo } from "@/lib/offline/gate";
import { PERFIL_ESTANDAR_DEFAULT } from "@/types/perfilOperativo";

describe("isCacheDegradadoActivo", () => {
  it("activo solo en especial con flag true", () => {
    expect(
      isCacheDegradadoActivo("especial", { ...PERFIL_ESTANDAR_DEFAULT, cache_degradado: true }),
    ).toBe(true);
  });

  it("inactivo en estándar aunque el flag sea true", () => {
    expect(
      isCacheDegradadoActivo("estandar", { ...PERFIL_ESTANDAR_DEFAULT, cache_degradado: true }),
    ).toBe(false);
  });

  it("inactivo en especial con flag false", () => {
    expect(
      isCacheDegradadoActivo("especial", { ...PERFIL_ESTANDAR_DEFAULT, cache_degradado: false }),
    ).toBe(false);
  });

  it("activo en especial demo aunque cache_degradado no venga en API", () => {
    expect(
      isCacheDegradadoActivo("especial", {
        ...PERFIL_ESTANDAR_DEFAULT,
        cache_degradado: undefined as unknown as boolean,
        plantilla_origen: "modo_especial_demo",
      }),
    ).toBe(true);
  });
});
