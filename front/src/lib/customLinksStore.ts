import { create } from "zustand";
import { persist } from "zustand/middleware";

export type CustomLink = {
  id: 1 | 2 | 3;
  name: string;
  url: string;
  visible: boolean;
};

type CustomLinksState = {
  links: CustomLink[];
  setLink: (id: 1 | 2 | 3, payload: { name: string; url: string }) => void;
  setVisibility: (id: 1 | 2 | 3, visible: boolean) => void;
  removeLink: (id: 1 | 2 | 3) => void;
  clearLinks: () => void;
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
      },
      setVisibility: (id, visible) => {
        const next = get().links.map((l) => (l.id === id ? { ...l, visible } : l));
        set({ links: next });
      },
      removeLink: (id) => {
        const next = get().links.filter((l) => l.id !== id);
        set({ links: next });
      },
      clearLinks: () => set({ links: [] }),
    }),
    { name: "custom-links-storage" }
  )
);
