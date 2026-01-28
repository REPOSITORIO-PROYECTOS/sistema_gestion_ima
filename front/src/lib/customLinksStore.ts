import { create } from "zustand";
import { persist } from "zustand/middleware";
import { API_CONFIG } from "@/lib/api-config";
import { useAuthStore } from "@/lib/authStore";

export type CustomLink = {
  id: 1 | 2 | 3;
  name: string;
  url: string;
  visible: boolean;
};

type CustomLinksState = {
  links: CustomLink[];
  // Actions locales
  setLink: (id: 1 | 2 | 3, payload: { name: string; url: string }) => void;
  setVisibility: (id: 1 | 2 | 3, visible: boolean) => void;
  removeLink: (id: 1 | 2 | 3) => void;
  clearLinks: () => void;
  
  // Acciones de sincronización
  syncWithBackend: () => Promise<void>;
  loadFromBackend: (configuracion: any) => void;
};

// Función auxiliar para guardar en backend
const saveToBackend = async (links: CustomLink[]) => {
  const token = useAuthStore.getState().token;
  if (!token) return;

  try {
    await fetch(`${API_CONFIG.BASE_URL}/users/me/config`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        configuracion: { custom_links: links }
      })
    });
  } catch (error) {
    console.error("Error syncing custom links:", error);
  }
};

export const useCustomLinksStore = create(
  persist<CustomLinksState>(
    (set, get) => ({
      links: [],
      
      setLink: (id, payload) => {
        const current = get().links;
        const next = [
          ...current.filter((l) => l.id !== id),
          { id, name: payload.name || `Enlace ${id}`, url: payload.url, visible: true },
        ].sort((a, b) => a.id - b.id);
        
        set({ links: next });
        saveToBackend(next);
      },

      setVisibility: (id, visible) => {
        const next = get().links.map((l) => (l.id === id ? { ...l, visible } : l));
        set({ links: next });
        saveToBackend(next);
      },

      removeLink: (id) => {
        const next = get().links.filter((l) => l.id !== id);
        set({ links: next });
        saveToBackend(next);
      },

      clearLinks: () => {
        set({ links: [] });
        saveToBackend([]);
      },

      syncWithBackend: async () => {
        const links = get().links;
        await saveToBackend(links);
      },

      loadFromBackend: (configuracion: any) => {
        if (configuracion && configuracion.custom_links) {
           // Validamos que sea un array para evitar errores
           if (Array.isArray(configuracion.custom_links)) {
             set({ links: configuracion.custom_links });
           }
        }
      }
    }),
    { name: "custom-links-storage" }
  )
);
