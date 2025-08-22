import api from '@/services/api';
import {
  Daemon,
  DaemonLog,
  DaemonJobHistory,
  DaemonUpdateRequest,
  DaemonHealthResponse,
  DaemonStatistics,
  DaemonError,
  DaemonActivity,
  DaemonMetric,
  LogLevel,
} from '@/types/daemon';

const daemonService = {
  // Get all daemons
  async getAllDaemons(): Promise<Daemon[]> {
    const response = await api.get('/daemons');
    return response.data;
  },

  // Get a specific daemon
  async getDaemon(daemonId: string): Promise<Daemon> {
    const response = await api.get(`/daemons/${daemonId}`);
    return response.data;
  },

  // Start a daemon
  async startDaemon(daemonId: string): Promise<{ message: string }> {
    const response = await api.post(`/daemons/${daemonId}/start`);
    return response.data;
  },

  // Stop a daemon
  async stopDaemon(daemonId: string): Promise<{ message: string }> {
    const response = await api.post(`/daemons/${daemonId}/stop`);
    return response.data;
  },

  // Restart a daemon
  async restartDaemon(daemonId: string): Promise<{ message: string }> {
    const response = await api.post(`/daemons/${daemonId}/restart`);
    return response.data;
  },

  // Stop all running daemons
  async stopAllDaemons(): Promise<{
    message: string;
    stopped_count: number;
    errors?: string[];
  }> {
    const response = await api.post('/daemons/stop-all');
    return response.data;
  },

  // Update daemon configuration
  async updateDaemon(
    daemonId: string,
    update: DaemonUpdateRequest
  ): Promise<Daemon> {
    const response = await api.put(`/daemons/${daemonId}`, update);
    return response.data;
  },

  // Get daemon default configuration
  async getDaemonDefaultConfig(
    daemonId: string
  ): Promise<Record<string, unknown>> {
    const response = await api.get(`/daemons/${daemonId}/default-config`);
    return response.data;
  },

  // Get daemon logs
  async getDaemonLogs(
    daemonId: string,
    params?: {
      limit?: number;
      level?: LogLevel;
      since?: string;
    }
  ): Promise<DaemonLog[]> {
    const response = await api.get(`/daemons/${daemonId}/logs`, {
      params,
    });
    return response.data;
  },

  // Get daemon job history
  async getDaemonJobHistory(
    daemonId: string,
    params?: {
      limit?: number;
      since?: string;
    }
  ): Promise<DaemonJobHistory[]> {
    const response = await api.get(`/daemons/${daemonId}/history`, {
      params,
    });
    return response.data;
  },

  // Check daemon health
  async checkDaemonHealth(): Promise<DaemonHealthResponse> {
    const response = await api.get('/daemons/health/check');
    return response.data;
  },

  // Get daemon statistics
  async getDaemonStatistics(daemonId: string): Promise<DaemonStatistics> {
    const response = await api.get(`/daemons/${daemonId}/statistics`);
    return response.data;
  },

  // Get daemon errors
  async getDaemonErrors(
    daemonId: string,
    params?: {
      limit?: number;
      unresolved_only?: boolean;
    }
  ): Promise<DaemonError[]> {
    const response = await api.get(`/daemons/${daemonId}/errors`, {
      params,
    });
    return response.data;
  },

  // Resolve daemon error
  async resolveDaemonError(
    daemonId: string,
    errorId: string
  ): Promise<{ message: string; error: DaemonError }> {
    const response = await api.post(
      `/daemons/${daemonId}/errors/${errorId}/resolve`
    );
    return response.data;
  },

  // Get daemon activities
  async getDaemonActivities(
    daemonId: string,
    params?: {
      limit?: number;
      severity?: string;
    }
  ): Promise<DaemonActivity[]> {
    const response = await api.get(`/daemons/${daemonId}/activities`, {
      params,
    });
    return response.data;
  },

  // Get all daemon activities
  async getAllDaemonActivities(params?: {
    limit?: number;
    severity?: string;
  }): Promise<DaemonActivity[]> {
    const response = await api.get('/daemons/activities/all', {
      params,
    });
    return response.data;
  },

  // Get daemon metrics
  async getDaemonMetrics(
    daemonId: string,
    params?: {
      metric_name?: string;
      since?: string;
      limit?: number;
    }
  ): Promise<DaemonMetric[]> {
    const response = await api.get(`/daemons/${daemonId}/metrics`, {
      params,
    });
    return response.data;
  },
};

export default daemonService;
