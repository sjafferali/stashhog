// Removed duplicate interfaces - they are now in models.ts

export interface ApiError {
  detail: string;
  status?: number;
  type?: string;
  loc?: string[];
  msg?: string;
}

export interface BatchOperationResult {
  success: number;
  failed: number;
  errors: Array<{
    id: number | string;
    error: string;
  }>;
}

export interface AnalysisRequest {
  scene_ids: number[];
  plan_id?: number;
}

export interface SyncRequest {
  full_sync?: boolean;
  sync_scenes?: boolean;
}

export interface SettingsUpdateRequest {
  stash_url?: string;
  stash_api_key?: string;
  openai_api_key?: string;
  openai_model?: string;
  openai_temperature?: number;
  openai_max_tokens?: number;
  auto_analyze_new_scenes?: boolean;
  default_analysis_plan_id?: number;
  sync_interval_hours?: number;
  enable_websocket_notifications?: boolean;
  log_level?: string;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  version?: string;
  error?: string;
}

// Re-export from models for convenience
export type { PaginatedResponse, FilterParams } from './models';
