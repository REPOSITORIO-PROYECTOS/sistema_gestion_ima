/* Store de Autenticación */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Tipos de usuario
export type Role = 'admin' | 'cajero' | 'contable' | 'stock' | 'cliente'

// Declaración de tipos de la Store
interface AuthState {
  
  role: Role | null                 // Tupla para Rol 
  setRole: (role: Role) => void     // Funcion que toma un rol como arg y devuelve void
  logout: () => void                // Funcion que toma un rol como arg y devuelve void

  // Funciones para hidratación - con token se van ?
  hasHydrated: boolean
  setHasHydrated: (val: boolean) => void
}


// Exportamos Estado para la App
export const useAuthStore = create<AuthState>()( 
  persist(
    (set) => ({
      role: null,
      setRole: (role) => set({ role }),
      logout: () => set({ role: null }),
      hasHydrated: false,
      setHasHydrated: (val) => set({ hasHydrated: val })
    }),

    // Logica hidratacion y persistencia
    {
      name: 'auth-storage',
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      }
    }
  )
)