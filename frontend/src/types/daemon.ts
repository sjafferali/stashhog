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
  MONITORED = 'MONITORED',
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

// WebSocket message types
export type DaemonWebSocketMessage =
  | { type: 'daemon_update'; daemon: Daemon }
  | { type: 'daemon_log'; daemon_id: string; log: DaemonLog }
  | {
      type: 'daemon_status';
      daemon_id: string;
      status: Record<string, unknown>;
    }
  | { type: 'daemon_job_action'; daemon_id: string; action: DaemonJobHistory }
  | { type: 'subscription_confirmed'; daemon_id: string }
  | { type: 'unsubscription_confirmed'; daemon_id: string }
  | { type: 'error'; message: string };
