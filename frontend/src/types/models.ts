export interface Scene {
  id: number
  stash_id: string
  title: string
  date?: string
  url?: string
  details?: string
  director?: string
  duration?: number
  file_mod_time?: string
  o_counter?: number
  organized: boolean
  path: string
  phash?: string
  rating?: number
  size?: string
  width?: number
  height?: number
  framerate?: number
  bitrate?: number
  codec?: string
  studio_id?: number
  galleries?: Gallery[]
  performers?: Performer[]
  tags?: Tag[]
  created_at: string
  updated_at: string
  analyzed_at?: string
  analysis_results?: AnalysisResult[]
  studio?: Studio
}

export interface Performer {
  id: number
  stash_id: string
  name: string
  url?: string
  gender?: string
  birthdate?: string
  ethnicity?: string
  country?: string
  eye_color?: string
  height?: string
  measurements?: string
  fake_tits?: string
  tattoos?: string
  piercings?: string
  aliases?: string
  favorite: boolean
  details?: string
  hair_color?: string
  weight?: string
  created_at: string
  updated_at: string
  scene_count?: number
}

export interface Tag {
  id: number
  stash_id: string
  name: string
  aliases?: string[]
  created_at: string
  updated_at: string
  scene_count?: number
  parent_tags?: Tag[]
  child_tags?: Tag[]
}

export interface Studio {
  id: number
  stash_id: string
  name: string
  url?: string
  details?: string
  created_at: string
  updated_at: string
  scene_count?: number
  parent_studio?: Studio
}

export interface Gallery {
  id: number
  stash_id: string
  title?: string
  url?: string
  date?: string
  details?: string
  studio_id?: number
  scene_id?: number
  path: string
  created_at: string
  updated_at: string
}

export interface AnalysisPlan {
  id: number
  name: string
  description?: string
  prompt_template: string
  model: string
  temperature: number
  max_tokens?: number
  extract_performers: boolean
  extract_tags: boolean
  extract_studio: boolean
  extract_title: boolean
  extract_date: boolean
  extract_details: boolean
  custom_fields?: Record<string, any>
  active: boolean
  created_at: string
  updated_at: string
}

export interface AnalysisResult {
  id: number
  scene_id: number
  plan_id: number
  model_used: string
  prompt_used: string
  raw_response: string
  extracted_data: {
    title?: string
    date?: string
    details?: string
    performers?: string[]
    tags?: string[]
    studio?: string
    custom_fields?: Record<string, any>
  }
  confidence_scores?: Record<string, number>
  processing_time: number
  created_at: string
  plan?: AnalysisPlan
}

export interface Job {
  id: string
  name: string
  type: 'sync' | 'analysis' | 'batch_analysis'
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  total: number
  error?: string
  result?: any
  created_at: string
  started_at?: string
  completed_at?: string
  metadata?: Record<string, any>
}

export interface SyncStatus {
  is_syncing: boolean
  last_sync?: string
  total_scenes: number
  total_performers: number
  total_tags: number
  total_studios: number
  scenes_to_analyze: number
  current_job?: Job
}

export interface Settings {
  stash_url: string
  stash_api_key?: string
  openai_api_key?: string
  openai_model: string
  openai_temperature: number
  openai_max_tokens?: number
  auto_analyze_new_scenes: boolean
  default_analysis_plan_id?: number
  sync_interval_hours?: number
  enable_websocket_notifications: boolean
  log_level: string
}

// Add these missing interfaces
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export interface FilterParams {
  page?: number
  size?: number
  search?: string
  sort_by?: string
  sort_dir?: 'asc' | 'desc'
  [key: string]: any
}