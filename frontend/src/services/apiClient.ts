import api from './api';
import {
  Scene,
  Performer,
  Tag,
  Studio,
  AnalysisPlan,
  Job,
  PaginatedResponse,
  FilterParams,
  SyncStatus,
  AnalysisResult,
  Settings,
} from '@/types/models';

class ApiClient {
  // Scenes
  async getScenes(params?: FilterParams): Promise<PaginatedResponse<Scene>> {
    const response = await api.get('/scenes', { params });
    return response.data;
  }

  async getScene(id: number): Promise<Scene> {
    const response = await api.get(`/scenes/${id}`);
    return response.data;
  }

  async updateScene(id: number, data: Partial<Scene>): Promise<Scene> {
    const response = await api.patch(`/scenes/${id}`, data);
    return response.data;
  }

  async analyzeScene(id: number, planId?: number): Promise<Job> {
    const response = await api.post(`/scenes/${id}/analyze`, {
      plan_id: planId,
    });
    return response.data;
  }

  // Performers
  async getPerformers(
    params?: FilterParams
  ): Promise<PaginatedResponse<Performer>> {
    const response = await api.get('/entities/performers', { params });
    return response.data;
  }

  async getPerformer(id: number): Promise<Performer> {
    const response = await api.get(`/entities/performers/${id}`);
    return response.data;
  }

  // Tags
  async getTags(params?: FilterParams): Promise<PaginatedResponse<Tag>> {
    const response = await api.get('/entities/tags', { params });
    return response.data;
  }

  async getTag(id: number): Promise<Tag> {
    const response = await api.get(`/entities/tags/${id}`);
    return response.data;
  }

  // Studios
  async getStudios(params?: FilterParams): Promise<PaginatedResponse<Studio>> {
    const response = await api.get('/entities/studios', { params });
    return response.data;
  }

  async getStudio(id: number): Promise<Studio> {
    const response = await api.get(`/entities/studios/${id}`);
    return response.data;
  }

  // Analysis
  async getAnalysisStats(): Promise<{
    total_scenes: number;
    analyzed_scenes: number;
    total_plans: number;
    pending_plans: number;
    pending_analysis: number;
  }> {
    const response = await api.get('/analysis/stats');
    return response.data;
  }

  async getAnalysisPlans(): Promise<AnalysisPlan[]> {
    const response = await api.get('/analysis/plans');
    return response.data.items || [];
  }

  async getAnalysisPlan(id: number): Promise<AnalysisPlan> {
    const response = await api.get(`/analysis/plans/${id}`);
    return response.data;
  }

  async updateAnalysisPlan(
    id: number,
    data: Partial<AnalysisPlan>
  ): Promise<AnalysisPlan> {
    const response = await api.put(`/analysis/plans/${id}`, data);
    return response.data;
  }

  async deleteAnalysisPlan(id: number): Promise<void> {
    await api.delete(`/analysis/plans/${id}`);
  }

  async cancelAnalysisPlan(id: number): Promise<void> {
    await api.patch(`/analysis/plans/${id}/cancel`);
  }

  async bulkUpdateAnalysisPlan(
    id: number,
    action: 'accept_all' | 'reject_all',
    sceneId?: string
  ): Promise<{ updated_count: number }> {
    const response = await api.post(`/analysis/plans/${id}/bulk-update`, {
      action,
      scene_id: sceneId,
    });
    return response.data;
  }

  async analyzeMultipleScenes(
    sceneIds: number[],
    planId?: number
  ): Promise<Job[]> {
    const response = await api.post('/analysis/batch', {
      scene_ids: sceneIds,
      plan_id: planId,
    });
    return response.data;
  }

  async analyzeScenes(params: {
    scene_ids?: string[];
    filters?: FilterParams;
    options: {
      detect_performers: boolean;
      detect_studios: boolean;
      detect_tags: boolean;
      detect_details: boolean;
      detect_video_tags: boolean;
      confidence_threshold: number;
    };
    plan_name?: string;
    background?: boolean;
  }): Promise<{
    job_id?: string;
    plan_id?: string;
    status: string;
    message?: string;
    total_scenes?: number;
    total_changes?: number;
  }> {
    const response = await api.post('/analysis/generate', params);
    return response.data;
  }

  async getAnalysisResults(sceneId: number): Promise<AnalysisResult[]> {
    const response = await api.get(`/analysis/results/${sceneId}`);
    return response.data;
  }

  // Jobs
  async getJobs(params?: FilterParams): Promise<Job[]> {
    const response = await api.get('/jobs', { params });
    return response.data.jobs || [];
  }

  async getJob(id: string): Promise<Job> {
    const response = await api.get(`/jobs/${id}`);
    return response.data;
  }

  async cancelJob(id: string): Promise<void> {
    await api.post(`/jobs/${id}/cancel`);
  }

  async retryJob(id: string): Promise<Job> {
    const response = await api.post(`/jobs/${id}/retry`);
    return response.data;
  }

  async getJobHandledDownloads(id: string): Promise<{
    job_id: string;
    total_downloads: number;
    downloads: Array<{
      id: number;
      timestamp: string;
      download_name: string;
      destination_path: string;
    }>;
  }> {
    const response = await api.get(`/jobs/${id}/handled-downloads`);
    return response.data;
  }

  async runManualCleanup(): Promise<{ job_id: string }> {
    const response = await api.post('/jobs/cleanup');
    return response.data;
  }

  async getRecentProcessedTorrents(limit?: number): Promise<{
    total: number;
    torrents: Array<{
      name: string;
      file_count: number;
      processed_at: string;
    }>;
  }> {
    const response = await api.get('/jobs/recent-processed-torrents', {
      params: { limit },
    });
    return response.data;
  }

  async runJob(
    jobType: string,
    metadata?: Record<string, unknown>
  ): Promise<{
    success: boolean;
    message: string;
    job_id: string;
    job_type: string;
    metadata: Record<string, unknown>;
  }> {
    const response = await api.post('/jobs/run', {
      job_type: jobType,
      metadata,
    });
    return response.data;
  }

  async applyAllApprovedChanges(): Promise<{
    job_id?: string;
    plans_affected: number;
    total_changes: number;
    message: string;
  }> {
    const response = await api.post('/analysis/apply-all-approved');
    return response.data;
  }

  // Settings
  async getSettings(): Promise<Settings> {
    const response = await api.get('/settings');
    const settingsArray = response.data;

    // Transform array of settings to Settings object
    const settingsMap: Record<string, string | number | boolean> = {};
    settingsArray.forEach(
      (setting: { key: string; value: string | number | boolean }) => {
        const key = setting.key.replace(/\./g, '_');
        // Use the actual value from the setting
        settingsMap[key] = setting.value;
      }
    );

    // Return as Settings object with defaults for any missing values
    return {
      stash_url: settingsMap.stash_url || '',
      stash_api_key: settingsMap.stash_api_key,
      openai_api_key: settingsMap.openai_api_key,
      openai_model: settingsMap.openai_model || 'gpt-4',
      openai_temperature:
        parseFloat(String(settingsMap.openai_temperature)) || 0.7,
      openai_max_tokens: settingsMap.openai_max_tokens
        ? parseInt(String(settingsMap.openai_max_tokens))
        : undefined,
      auto_analyze_new_scenes:
        settingsMap.auto_analyze_new_scenes === 'true' ||
        settingsMap.auto_analyze_new_scenes === true,
      default_analysis_plan_id: settingsMap.default_analysis_plan_id
        ? parseInt(String(settingsMap.default_analysis_plan_id))
        : undefined,
      sync_interval_hours: settingsMap.sync_interval_hours
        ? parseInt(String(settingsMap.sync_interval_hours))
        : undefined,
      enable_websocket_notifications:
        settingsMap.enable_websocket_notifications === 'true' ||
        settingsMap.enable_websocket_notifications === true,
      log_level: settingsMap.log_level || 'info',
    } as Settings;
  }

  async updateSetting(
    key: string,
    value: string | number | boolean | null
  ): Promise<void> {
    await api.put('/settings', { [key]: value });
  }

  async testStashConnection(): Promise<{ success: boolean; message: string }> {
    const response = await api.post('/settings/test-connection');
    return response.data;
  }

  // Sync
  async getSyncStatus(): Promise<SyncStatus> {
    const response = await api.get('/sync/stats');
    return response.data;
  }

  async startSync(): Promise<Job> {
    const response = await api.post('/sync/all');
    return response.data;
  }

  async stopSync(): Promise<void> {
    await api.post('/sync/stop');
  }

  async getSyncHistory(params?: FilterParams): Promise<PaginatedResponse<Job>> {
    const response = await api.get('/sync/history', { params });
    return response.data;
  }
}

export const apiClient = new ApiClient();
export default apiClient;
