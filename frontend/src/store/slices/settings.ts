import { StateCreator } from 'zustand'
import { apiClient } from '@/services/apiClient'

export interface SettingsSlice {
  settings: Record<string, any>
  isLoaded: boolean
  loadSettings: () => Promise<void>
  updateSetting: (key: string, value: any) => Promise<void>
  getSetting: (key: string) => any
}

export const createSettingsSlice: StateCreator<SettingsSlice> = (set, get) => ({
  settings: {},
  isLoaded: false,

  loadSettings: async () => {
    try {
      const response = await apiClient.getSettings()
      set({ settings: response, isLoaded: true })
    } catch (error) {
      console.error('Failed to load settings:', error)
      set({ isLoaded: true })
    }
  },

  updateSetting: async (key, value) => {
    try {
      await apiClient.updateSetting(key, value)
      set((state) => ({
        settings: {
          ...state.settings,
          [key]: value,
        },
      }))
    } catch (error) {
      console.error('Failed to update setting:', error)
      throw error
    }
  },

  getSetting: (key) => {
    return get().settings[key]
  },
})