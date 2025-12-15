import { create } from "zustand";
import { persist } from "zustand/middleware";

interface FeaturesState {
  mesasEnabled: boolean;
  setMesasEnabled: (val: boolean) => void;
  toggleMesasEnabled: () => void;
}

export const useFeaturesStore = create<FeaturesState>()(
  persist(
    (set, get) => ({
      mesasEnabled: false,
      setMesasEnabled: (val) => set({ mesasEnabled: val }),
      toggleMesasEnabled: () => set({ mesasEnabled: !get().mesasEnabled }),
    }),
    { name: "features-storage" }
  )
);
