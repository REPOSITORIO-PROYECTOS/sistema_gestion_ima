import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Usuario {
  id: number
  nombre_usuario: string        
  apellido: string
  email: string
  rol: Role
  activo: boolean;
  id_empresa: number;
}

// Tipos de usuario
export interface Role {
  id: number
  nombre: "Admin" | "Cajero" | "Cliente" | "Gerente"
}

interface AuthState {

  token: string | null
  role: Role | null
  nombre_usuario: string | null
  usuario: Usuario | null

  setToken: (token: string) => void
  setRole: (role: Role) => void
  setNombreUsuario: (name: string) => void
  setUsuario: (usuario: Usuario) => void

  logout: () => void

  hasHydrated: boolean
  setHasHydrated: (val: boolean) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      role: null,
      nombre_usuario: null,
      usuario: null,

      setToken: (token) => set({ token }),
      setRole: (role) => set({ role }),
      setNombreUsuario: (name) => set({ nombre_usuario: name }),
      setUsuario: (usuario) => set({ usuario }),

      logout: () => set({ token: null, role: null, nombre_usuario: null, usuario: null }),

      hasHydrated: false,
      setHasHydrated: (val) => set({ hasHydrated: val }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        role: state.role,
        nombre_usuario: state.nombre_usuario,
        usuario: state.usuario,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      },
    }
  )
)