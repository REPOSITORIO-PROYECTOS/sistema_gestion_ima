import { mensajeSnapshotDesactualizado } from "@/lib/offline/offline-meta-format";

describe("offline-meta-format", () => {
  it("muestra antigüedad del snapshot", () => {
    const haceDosDias = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString();
    expect(mensajeSnapshotDesactualizado(haceDosDias)).toContain("hace 2 días");
  });
});
