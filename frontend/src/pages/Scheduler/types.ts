export interface Schedule {
  id: number;
  name: string;
  description?: string;
  task_type: 'sync' | 'analysis' | 'cleanup';
  schedule: string; // cron expression
  config: TaskConfig;
  enabled: boolean;
  last_run?: Date;
  next_run?: Date;
  created_at: Date;
  updated_at?: Date;
}

export interface ScheduleRun {
  id: number;
  schedule_id: number;
  started_at: Date;
  completed_at?: Date;
  status: 'success' | 'failed' | 'running' | 'cancelled';
  job_id?: string;
  result?: Record<string, unknown>;
  error?: string;
  duration?: number; // in seconds
}

export interface CreateScheduleData {
  name: string;
  description?: string;
  task_type: Schedule['task_type'];
  schedule: string;
  config: TaskConfig;
  enabled?: boolean;
}

export interface UpdateScheduleData {
  name?: string;
  description?: string;
  schedule?: string;
  config?: TaskConfig;
  enabled?: boolean;
}

export interface ScheduleStats {
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
  average_duration: number;
  last_run?: ScheduleRun;
}

export interface NotificationSettings {
  email_on_failure?: boolean;
  email_on_success?: boolean;
  webhook_url?: string;
}

export interface TaskConfig {
  // Sync task config
  full_sync?: boolean;
  entity_types?: string[];
  force_update?: boolean;

  // Analysis task config
  scene_filters?: {
    min_duration?: number;
    tags?: string[];
    performers?: string[];
  };
  analysis_options?: {
    enable_deduplication?: boolean;
    enable_quality_check?: boolean;
    enable_tagging?: boolean;
  };
  plan_name_template?: string;
  auto_apply_threshold?: number;

  // Cleanup task config
  older_than_days?: number;
  cleanup_types?: string[];
}

export interface SchedulePreset {
  name: string;
  expression: string;
  description: string;
}

export const SCHEDULE_PRESETS: SchedulePreset[] = [
  {
    name: 'Every hour',
    expression: '0 * * * *',
    description: 'Runs at the start of every hour',
  },
  {
    name: 'Every 30 minutes',
    expression: '*/30 * * * *',
    description: 'Runs every 30 minutes',
  },
  {
    name: 'Daily at midnight',
    expression: '0 0 * * *',
    description: 'Runs every day at midnight',
  },
  {
    name: 'Daily at 3 AM',
    expression: '0 3 * * *',
    description: 'Runs every day at 3 AM',
  },
  {
    name: 'Weekly on Sunday',
    expression: '0 0 * * 0',
    description: 'Runs every Sunday at midnight',
  },
  {
    name: 'Monthly on 1st',
    expression: '0 0 1 * *',
    description: 'Runs on the 1st of every month',
  },
  {
    name: 'Every weekday',
    expression: '0 9 * * 1-5',
    description: 'Runs Monday-Friday at 9 AM',
  },
];
