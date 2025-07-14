import { StateCreator } from 'zustand'

export interface Notification {
  type: 'success' | 'error' | 'info' | 'warning'
  content: string
}

export interface AppSlice {
  isLoading: boolean
  error: string | null
  notification: Notification | null
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setNotification: (notification: Notification | null) => void
  showNotification: (notification: Notification) => void
}

export const createAppSlice: StateCreator<AppSlice> = (set) => ({
  isLoading: false,
  error: null,
  notification: null,
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error }),
  
  setNotification: (notification) => set({ notification }),
  
  showNotification: (notification) => {
    set({ notification })
    // Auto-clear notification after a delay
    setTimeout(() => {
      set({ notification: null })
    }, 5000)
  },
})