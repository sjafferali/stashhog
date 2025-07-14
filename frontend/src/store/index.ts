import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { AppSlice, createAppSlice } from './slices/app'
import { SettingsSlice, createSettingsSlice } from './slices/settings'

export type StoreState = AppSlice & SettingsSlice

const useAppStore = create<StoreState>()(
  devtools(
    (...a) => ({
      ...createAppSlice(...a),
      ...createSettingsSlice(...a),
    }),
    {
      name: 'app-store',
    }
  )
)

export default useAppStore