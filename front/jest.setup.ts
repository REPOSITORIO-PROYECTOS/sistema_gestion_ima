import "@testing-library/jest-dom";

if (typeof globalThis.Response === "undefined") {
  class MiniResponse {
    status: number;
    ok: boolean;
    private readonly raw: string;

    constructor(body?: BodyInit | null, init?: ResponseInit) {
      this.raw = typeof body === "string" ? body : "";
      this.status = init?.status ?? 200;
      this.ok = this.status >= 200 && this.status < 300;
    }

    async json(): Promise<unknown> {
      return JSON.parse(this.raw);
    }
  }

  globalThis.Response = MiniResponse as unknown as typeof Response;
}

if (typeof globalThis.structuredClone !== "function") {
  globalThis.structuredClone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;
}
