// Removed duplicate interfaces - they are now in models.ts

export interface ApiError {
  detail: string
  status?: number
  type?: string
  loc?: string[]
  msg?: string
}

export interface BatchOperationResult {
  success: number
  failed: number
  errors: Array<{
    id: number | string
    error: string
  }>
}

export interface AnalysisRequest {
  scene_ids: number[]
  plan_id?: number
}

export interface SyncRequest {
  full_sync?: boolean
  sync_scenes?: boolean
  sync_performers?: boolean
  sync_tags?: boolean
  sync_studios?: boolean
}

export interface SettingsUpdateRequest {
  [key: string]: any
}

export interface ConnectionTestResult {
  success: boolean
  message: string
  version?: string
  error?: string
}

// Re-export from models for convenience
export type { PaginatedResponse, FilterParams } from './models'