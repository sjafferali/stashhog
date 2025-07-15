import { StateCreator } from 'zustand';
import { apiClient } from '@/services/apiClient';
import { Settings } from '@/types/models';

export interface SettingsSlice {
  settings: Settings | null;
  isLoaded: boolean;
  loadSettings: () => Promise<void>;
  updateSetting: (
    key: string,
    value: string | number | boolean | null
  ) => Promise<void>;
  getSetting: (key: string) => string | number | boolean | null | undefined;
}

export const createSettingsSlice: StateCreator<SettingsSlice> = (set, get) => ({
  settings: null,
  isLoaded: false,

  loadSettings: async () => {
    try {
      const response = await apiClient.getSettings();
      set({ settings: response, isLoaded: true });
    } catch (error) {
      console.error('Failed to load settings:', error);
      set({ isLoaded: true });
    }
  },

  updateSetting: async (key, value) => {
    try {
      await apiClient.updateSetting(key, value);
      set((state) => ({
        settings: state.settings
          ? {
              ...state.settings,
              [key as keyof Settings]: value,
            }
          : null,
      }));
    } catch (error) {
      console.error('Failed to update setting:', error);
      throw error;
    }
  },

  getSetting: (key) => {
    const settings = get().settings;
    return settings ? settings[key as keyof Settings] : undefined;
  },
});
