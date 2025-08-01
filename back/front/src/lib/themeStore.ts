// lib/themeStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type ThemeState = {
  navbarColor: string
  logoUrl: string
  setNavbarColor: (color: string) => void
  setLogoUrl: (url: string) => void
}

export const useThemeStore = create<ThemeState>()(
    
  persist(
    (set) => ({
      navbarColor: 'bg-green-800',
      logoUrl: '/logo.png',
      setNavbarColor: (color) => set({ navbarColor: color }),
      setLogoUrl: (url) => set({ logoUrl: url }),
    }),
    {
      name: 'theme-storage', // clave en localStorage
    }
  )
)