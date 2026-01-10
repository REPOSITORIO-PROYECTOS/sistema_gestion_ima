import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react';
import Login from '@/app/page';

type AuthState = {
  setToken: jest.Mock;
  setUsuario: jest.Mock;
  setRole: jest.Mock;
};

type EmpresaState = {
  setEmpresa: jest.Mock;
  empresa: unknown | null;
};

type ProductoState = {
  setProductos: jest.Mock;
};

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock('@/lib/authStore', () => ({
  useAuthStore: <T,>(selector: (state: AuthState) => T) =>
    selector({
      setToken: jest.fn(),
      setUsuario: jest.fn(),
      setRole: jest.fn(),
    }),
}));

jest.mock('@/lib/empresaStore', () => ({
  useEmpresaStore: <T,>(selector: (state: EmpresaState) => T) =>
    selector({
      setEmpresa: jest.fn(),
      empresa: null,
    }),
}));

jest.mock('@/lib/productoStore', () => ({
  useProductoStore: <T,>(selector: (state: ProductoState) => T) =>
    selector({
      setProductos: jest.fn(),
    }),
}));

describe('Login retry flow', () => {
  beforeEach(() => {
    (global as unknown as { fetch: jest.Mock }).fetch = jest
      .fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access_token: 'token-123' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 1, nombre_usuario: 'admin', rol: { nombre: 'Admin', id: 1 } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id_empresa: 1, nombre_negocio: 'Demo' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ([] as unknown[]),
      });
  });

  it('should retry and succeed on second click attempt automatically', async () => {
    const { getByLabelText, getByText } = render(<Login />);
    fireEvent.change(getByLabelText('Usuario'), { target: { value: 'user' } });
    fireEvent.change(getByLabelText('Contraseña'), { target: { value: 'pass' } });
    fireEvent.click(getByText('Ingresar'));

    await waitFor(() => {
      expect((global as unknown as { fetch: jest.Mock }).fetch).toHaveBeenCalledTimes(5);
    });
  });
});
