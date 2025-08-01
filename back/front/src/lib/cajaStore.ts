// stores/cajaStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface CajaStore {
  cajaAbierta: boolean
  setCajaAbierta: (valor: boolean) => void
  clearCaja: () => void
}

export const useCajaStore = create<CajaStore>()(
  persist(
    (set) => ({
      cajaAbierta: false,
      setCajaAbierta: (valor) => set({ cajaAbierta: valor }),
      clearCaja: () => set({ cajaAbierta: false }),
    }),
    {
      name: 'caja-storage', 
    }
  )
)