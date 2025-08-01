import api from '@/services/api';
import {
  Daemon,
  DaemonLog,
  DaemonJobHistory,
  DaemonUpdateRequest,
  DaemonHealthResponse,
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

  // Update daemon configuration
  async updateDaemon(
    daemonId: string,
    update: DaemonUpdateRequest
  ): Promise<Daemon> {
    const response = await api.put(`/daemons/${daemonId}`, update);
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
};

export default daemonService;
