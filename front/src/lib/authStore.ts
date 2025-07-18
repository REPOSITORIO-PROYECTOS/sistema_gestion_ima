/* Store de Autenticación */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Tipos de usuario
export type Role = 'admin' | 'cajero' | 'contable' | 'stock' | 'cliente'

// Declaración de tipos de la Store
interface AuthState {

  token: string | null
  role: Role | null                 
  nombre_usuario: string | null

  setToken: (token: string) => void
  setRole: (role: Role) => void
  setNombreUsuario: (name: string) => void

  logout: () => void

  hasHydrated: boolean
  setHasHydrated: (val: boolean) => void
}


// Exportamos Estado para la App
export const useAuthStore = create<AuthState>()(

  persist(
    
    (set) => ({
      token: null,
      role: null,
      nombre_usuario: null,

      setToken: (token) => set({ token }),
      setRole: (role) => set({ role }),
      setNombreUsuario: (name) => set({ nombre_usuario: name }),

      logout: () => set({ token: null, role: null, nombre_usuario: null }),

      hasHydrated: false,
      setHasHydrated: (val) => set({ hasHydrated: val })
    }),
    {
      name: 'auth-storage',
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      }
    }
  )
)