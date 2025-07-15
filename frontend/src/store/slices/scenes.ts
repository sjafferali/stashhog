import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

export type ViewMode = 'grid' | 'list';
export type GridSize = 'small' | 'medium' | 'large';

interface ScenesState {
  // Selection state
  selectedScenes: Set<string>;

  // View preferences
  viewMode: ViewMode;
  gridSize: GridSize;

  // Actions
  selectScene: (id: string) => void;
  deselectScene: (id: string) => void;
  toggleSceneSelection: (id: string) => void;
  selectAllScenes: (ids: string[]) => void;
  clearSelection: () => void;
  setViewMode: (mode: ViewMode) => void;
  setGridSize: (size: GridSize) => void;
}

export const useScenesStore = create<ScenesState>()(
  devtools(
    persist(
      (set) => ({
        // Initial state
        selectedScenes: new Set<string>(),
        viewMode: 'grid',
        gridSize: 'medium',

        // Selection actions
        selectScene: (id) =>
          set((state) => ({
            selectedScenes: new Set(state.selectedScenes).add(id),
          })),

        deselectScene: (id) =>
          set((state) => {
            const newSet = new Set(state.selectedScenes);
            newSet.delete(id);
            return { selectedScenes: newSet };
          }),

        toggleSceneSelection: (id) =>
          set((state) => {
            const newSet = new Set(state.selectedScenes);
            if (newSet.has(id)) {
              newSet.delete(id);
            } else {
              newSet.add(id);
            }
            return { selectedScenes: newSet };
          }),

        selectAllScenes: (ids) =>
          set(() => ({
            selectedScenes: new Set(ids),
          })),

        clearSelection: () =>
          set(() => ({
            selectedScenes: new Set<string>(),
          })),

        // View preference actions
        setViewMode: (mode) => set({ viewMode: mode }),

        setGridSize: (size) => set({ gridSize: size }),
      }),
      {
        name: 'scenes-storage',
        // Only persist view preferences, not selection state
        partialize: (state) => ({
          viewMode: state.viewMode,
          gridSize: state.gridSize,
        }),
      }
    )
  )
);
