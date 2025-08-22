export interface Daemon {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  auto_start: boolean;
  status: DaemonStatus;
  configuration: Record<string, unknown>;
  started_at?: string;
  last_heartbeat?: string;
  created_at: string;
  updated_at: string;
}

export enum DaemonStatus {
  STOPPED = 'STOPPED',
  RUNNING = 'RUNNING',
  ERROR = 'ERROR',
}

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARNING = 'WARNING',
  ERROR = 'ERROR',
}

export interface DaemonLog {
  id: string;
  daemon_id: string;
  level: LogLevel;
  message: string;
  created_at: string;
}

export interface DaemonJobHistory {
  id: string;
  daemon_id: string;
  job_id: string; // Job IDs are stored as strings in the database
  action: DaemonJobAction;
  reason?: string;
  created_at: string;
}

export enum DaemonJobAction {
  LAUNCHED = 'LAUNCHED',
  CANCELLED = 'CANCELLED',
  FINISHED = 'FINISHED',
}

export interface DaemonUpdateRequest {
  configuration?: Record<string, unknown>;
  enabled?: boolean;
  auto_start?: boolean;
}

export interface DaemonHealthItem {
  id: string;
  name: string;
  uptime?: number;
  reason?: string;
  last_heartbeat?: string;
}

export interface DaemonHealthResponse {
  healthy: DaemonHealthItem[];
  unhealthy: DaemonHealthItem[];
  stopped: DaemonHealthItem[];
}

// Daemon statistics
export interface DaemonStatistics {
  id: string;
  daemon_id: string;
  current_activity?: string;
  current_progress?: number;
  items_processed: number;
  items_pending: number;
  last_error_message?: string;
  last_error_time?: string;
  error_count_24h: number;
  warning_count_24h: number;
  jobs_launched_24h: number;
  jobs_completed_24h: number;
  jobs_failed_24h: number;
  health_score: number;
  avg_job_duration_seconds?: number;
  uptime_percentage: number;
  last_successful_run?: string;
  updated_at: string;
}

// Daemon error
export interface DaemonError {
  id: string;
  daemon_id: string;
  error_type: string;
  error_message: string;
  error_details?: string;
  context?: Record<string, unknown>;
  occurrence_count: number;
  first_seen: string;
  last_seen: string;
  resolved: boolean;
  resolved_at?: string;
}

// Daemon activity
export interface DaemonActivity {
  id: string;
  daemon_id: string;
  daemon_name?: string;
  activity_type: string;
  message: string;
  details?: Record<string, unknown>;
  severity: 'info' | 'warning' | 'error';
  created_at: string;
}

// Daemon metric
export interface DaemonMetric {
  id: string;
  daemon_id: string;
  metric_name: string;
  metric_value: number;
  metric_unit?: string;
  timestamp: string;
}

// WebSocket message types
export type DaemonWebSocketMessage =
  | { type: 'daemon_update'; daemon: Daemon }
  | { type: 'daemon_log'; daemon_id: string; log: DaemonLog }
  | {
      type: 'daemon_status';
      daemon_id: string;
      status: DaemonStatistics;
    }
  | { type: 'daemon_job_action'; daemon_id: string; action: DaemonJobHistory }
  | { type: 'daemon_activity'; daemon_id: string; activity: DaemonActivity }
  | { type: 'activity_feed'; activity: DaemonActivity }
  | { type: 'daemon_alert'; daemon_id: string; alert: Record<string, unknown> }
  | { type: 'subscription_confirmed'; daemon_id: string }
  | { type: 'unsubscription_confirmed'; daemon_id: string }
  | { type: 'error'; message: string };
