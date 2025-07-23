export interface SceneMarker {
  id: string;
  title: string;
  seconds: number;
  end_seconds?: number;
  primary_tag: Tag;
  tags: Tag[];
  created_at?: string;
  updated_at?: string;
}

export interface SceneFile {
  id: string;
  path: string;
  basename?: string;
  is_primary: boolean;
  size?: number;
  format?: string;
  duration?: number;
  width?: number;
  height?: number;
  video_codec?: string;
  audio_codec?: string;
  frame_rate?: number;
  bit_rate?: number;
  oshash?: string;
  phash?: string;
  mod_time?: string;
}

export interface Scene {
  id: string;
  title: string;
  paths: string[];
  path?: string; // Legacy support for single path
  file_path?: string; // Actual file path from Stash
  organized: boolean;
  analyzed: boolean;
  video_analyzed: boolean;
  details?: string;
  stash_created_at: string;
  stash_updated_at?: string;
  stash_date?: string;
  last_synced: string;

  // File properties
  duration?: number;
  size?: number;
  width?: number;
  height?: number;
  framerate?: number;
  bitrate?: number;
  video_codec?: string;
  codec?: string; // Alias for video_codec
  date?: string;
  phash?: string;
  file_mod_time?: string;

  // Relationships
  studio?: Studio;
  performers: Performer[];
  tags: Tag[];
  markers: SceneMarker[];
  files: SceneFile[];

  // Analysis
  analysis_results?: AnalysisResult[];

  // Additional fields from frontend usage
  url?: string;
  rating?: number;
  created_at: string;
  updated_at: string;
}

export interface Performer {
  id: string;
  name: string;
  url?: string;
  gender?: string;
  birthdate?: string;
  ethnicity?: string;
  country?: string;
  eye_color?: string;
  height?: string;
  measurements?: string;
  fake_tits?: string;
  tattoos?: string;
  piercings?: string;
  aliases?: string;
  favorite: boolean;
  details?: string;
  hair_color?: string;
  weight?: string;
  created_at: string;
  updated_at: string;
  scene_count?: number;
}

export interface Tag {
  id: string;
  name: string;
  aliases?: string[];
  created_at: string;
  updated_at: string;
  scene_count?: number;
  parent_tags?: Tag[];
  child_tags?: Tag[];
}

export interface Studio {
  id: string;
  name: string;
  url?: string;
  details?: string;
  created_at: string;
  updated_at: string;
  scene_count?: number;
  parent_studio?: Studio;
}

export interface Gallery {
  id: string;
  title?: string;
  url?: string;
  date?: string;
  details?: string;
  studio_id?: string;
  scene_id?: string;
  path: string;
  created_at: string;
  updated_at: string;
}

export interface ApiUsage {
  total_cost: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_breakdown: Record<string, number>;
  token_breakdown: Record<
    string,
    {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
    }
  >;
  model?: string;
  scenes_analyzed?: number;
  average_cost_per_scene?: number;
}

export interface AnalysisPlan {
  id: number;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at?: string;
  total_scenes: number;
  total_changes: number;
  metadata?: Record<string, unknown> & {
    api_usage?: ApiUsage;
    scenes_analyzed?: number;
  };
  active?: boolean;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  extract_performers?: boolean;
  extract_tags?: boolean;
  extract_studio?: boolean;
  extract_title?: boolean;
  extract_date?: boolean;
  extract_details?: boolean;
  custom_fields?: Record<string, string | number | boolean | null>;
  prompt_template?: string;
  job_id?: string | null;
}

export interface AnalysisResult {
  id: number;
  scene_id: string;
  plan_id: number;
  model_used: string;
  prompt_used: string;
  raw_response: string;
  extracted_data: {
    title?: string;
    date?: string;
    details?: string;
    performers?: string[];
    tags?: string[];
    studio?: string;
    custom_fields?: Record<string, string | number | boolean | null>;
  };
  confidence_scores?: Record<string, number>;
  processing_time: number;
  created_at: string;
  plan?: AnalysisPlan;
}

export interface Job {
  id: string;
  name?: string;
  type:
    | 'scene_sync'
    | 'scene_analysis'
    | 'settings_test'
    | 'sync_all'
    | 'sync'
    | 'sync_scenes'
    | 'sync_performers'
    | 'sync_tags'
    | 'sync_studios'
    | 'analysis'
    | 'apply_plan';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  total?: number;
  processed_items?: number;
  parameters?: Record<string, unknown>;
  error?: string;
  result?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  metadata?: Record<string, string | number | boolean | null> & {
    last_message?: string;
    plan_id?: number;
  };
}

export interface ActionableItem {
  id: string;
  type: 'sync' | 'analysis' | 'organization' | 'system';
  title: string;
  description: string;
  count: number;
  action: string;
  action_label: string;
  route?: string;
  batch_size?: number;
  priority: 'high' | 'medium' | 'low';
  visible: boolean;
}

export interface DashboardJob {
  id: string;
  type: string;
  status: string;
  progress?: number;
  created_at?: string;
  completed_at?: string;
  error?: string;
  result?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface SyncStatus {
  summary: {
    scene_count: number;
    performer_count: number;
    tag_count: number;
    studio_count: number;
  };
  sync: {
    last_scene_sync?: string;
    last_performer_sync?: string;
    last_tag_sync?: string;
    last_studio_sync?: string;
    pending_scenes: number;
    is_syncing: boolean;
  };
  analysis: {
    scenes_not_analyzed: number;
    scenes_not_video_analyzed: number;
    draft_plans: number;
    reviewing_plans: number;
    is_analyzing: boolean;
  };
  organization: {
    unorganized_scenes: number;
  };
  metadata: {
    scenes_without_files: number;
    scenes_missing_details: number;
    scenes_without_studio: number;
    scenes_without_performers: number;
    scenes_without_tags: number;
  };
  jobs: {
    recent_failed_jobs: number;
    running_jobs: DashboardJob[];
    completed_jobs: DashboardJob[];
  };
  actionable_items: ActionableItem[];
}

export interface Settings {
  stash_url: string;
  stash_api_key?: string;
  openai_api_key?: string;
  openai_model: string;
  openai_temperature: number;
  openai_max_tokens?: number;
  auto_analyze_new_scenes: boolean;
  default_analysis_plan_id?: number;
  sync_interval_hours?: number;
  enable_websocket_notifications: boolean;
  log_level: string;
}

// Add these missing interfaces
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface FilterParams {
  page?: number;
  per_page?: number;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  [key: string]: string | number | boolean | string[] | undefined;
}

export interface ModelConfig {
  name: string;
  description: string;
  input_cost: number;
  cached_cost?: number;
  output_cost: number;
  context_window: number;
  max_output: number;
  category: string;
  supports_caching?: boolean;
}

export interface ModelsResponse {
  models: Record<string, ModelConfig>;
  categories: Record<string, string>;
  default: string;
  recommended: string[];
}

export interface CostResponse {
  plan_id: number;
  total_cost: number;
  total_tokens: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  cost_breakdown: Record<string, number>;
  token_breakdown: Record<
    string,
    {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
    }
  >;
  model?: string;
  scenes_analyzed?: number;
  average_cost_per_scene?: number;
  currency: string;
  message?: string;
}

export interface SyncLogEntry {
  id: number;
  sync_type: 'full' | 'incremental' | 'specific';
  had_changes: boolean;
  change_type: 'created' | 'updated' | 'skipped' | 'failed' | null;
  error_message: string | null;
  created_at: string;
  sync_history: {
    job_id: string;
    started_at: string;
    completed_at: string | null;
    status: string;
    items_synced: number;
    items_created: number;
    items_updated: number;
  };
}
