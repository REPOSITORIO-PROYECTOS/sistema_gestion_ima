import React from "react";
import { render, fireEvent, waitFor } from "@testing-library/react";
import { toast } from "sonner";
import Login from "@/app/page";

const mockPush = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("sonner", () => ({
  toast: { error: jest.fn(), success: jest.fn() },
}));

type AuthState = {
  setToken: jest.Mock;
  setUsuario: jest.Mock;
  setRole: jest.Mock;
};

type EmpresaState = {
  setEmpresa: jest.Mock;
  empresa: unknown | null;
};

const mockSetToken = jest.fn();
const mockSetUsuario = jest.fn();
const mockSetRole = jest.fn();
const mockSetEmpresa = jest.fn();

jest.mock("@/lib/authStore", () => ({
  useAuthStore: <T,>(selector: (state: AuthState) => T) =>
    selector({
      setToken: mockSetToken,
      setUsuario: mockSetUsuario,
      setRole: mockSetRole,
    }),
}));

jest.mock("@/lib/empresaStore", () => ({
  useEmpresaStore: <T,>(selector: (state: EmpresaState) => T) =>
    selector({
      setEmpresa: mockSetEmpresa,
      empresa: null,
    }),
}));

function fetchMock() {
  return (global as unknown as { fetch: jest.Mock }).fetch;
}

describe("Login", () => {
  beforeEach(() => {
    mockPush.mockClear();
    mockSetToken.mockClear();
    mockSetUsuario.mockClear();
    mockSetRole.mockClear();
    mockSetEmpresa.mockClear();
    jest.mocked(toast.error).mockClear();
  });

  it("no reintenta solo si la red falla: muestra el error y deja el botón listo", async () => {
    (global as unknown as { fetch: jest.Mock }).fetch = jest
      .fn()
      .mockRejectedValue(new TypeError("Failed to fetch"));

    const { getByLabelText, getByText } = render(<Login />);
    fireEvent.change(getByLabelText("Usuario"), { target: { value: "user" } });
    fireEvent.change(getByLabelText("Contraseña"), { target: { value: "pass" } });
    fireEvent.click(getByText("Ingresar"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Failed to fetch");
    });
    expect(fetchMock()).toHaveBeenCalledTimes(1);
    expect(fetchMock().mock.calls[0][0]).toContain("/auth/token");
    expect(getByText("Ingresar")).toBeEnabled();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("con credenciales válidas pide el token, el usuario y la empresa, y entra al dashboard", async () => {
    (global as unknown as { fetch: jest.Mock }).fetch = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: { get: () => null },
        json: async () => ({ access_token: "token-123" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: { get: () => null },
        json: async () => ({ id: 1, nombre_usuario: "admin", rol: { nombre: "Admin", id: 1 } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: { get: () => null },
        json: async () => ({ id_empresa: 1, nombre_negocio: "Demo" }),
      });

    const { getByLabelText, getByText } = render(<Login />);
    fireEvent.change(getByLabelText("Usuario"), { target: { value: "user" } });
    fireEvent.change(getByLabelText("Contraseña"), { target: { value: "pass" } });
    fireEvent.click(getByText("Ingresar"));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });

    const urls = fetchMock().mock.calls.map((call) => String(call[0]));
    expect(urls).toHaveLength(3);
    expect(urls[0]).toContain("/auth/token");
    expect(urls[1]).toContain("/users/me");
    expect(urls[2]).toContain("/configuracion/mi-empresa");
    expect(mockSetToken).toHaveBeenCalledWith("token-123");
    expect(mockSetEmpresa).toHaveBeenCalledWith({ id_empresa: 1, nombre_negocio: "Demo" });
  });
});
