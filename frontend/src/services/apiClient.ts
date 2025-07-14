import api from './api'
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
  Settings
} from '@/types/models'

class ApiClient {
  // Scenes
  async getScenes(params?: FilterParams): Promise<PaginatedResponse<Scene>> {
    const response = await api.get('/scenes', { params })
    return response.data
  }

  async getScene(id: number): Promise<Scene> {
    const response = await api.get(`/scenes/${id}`)
    return response.data
  }

  async updateScene(id: number, data: Partial<Scene>): Promise<Scene> {
    const response = await api.patch(`/scenes/${id}`, data)
    return response.data
  }

  async analyzeScene(id: number, planId?: number): Promise<Job> {
    const response = await api.post(`/scenes/${id}/analyze`, { plan_id: planId })
    return response.data
  }

  // Performers
  async getPerformers(params?: FilterParams): Promise<PaginatedResponse<Performer>> {
    const response = await api.get('/performers', { params })
    return response.data
  }

  async getPerformer(id: number): Promise<Performer> {
    const response = await api.get(`/performers/${id}`)
    return response.data
  }

  // Tags
  async getTags(params?: FilterParams): Promise<PaginatedResponse<Tag>> {
    const response = await api.get('/tags', { params })
    return response.data
  }

  async getTag(id: number): Promise<Tag> {
    const response = await api.get(`/tags/${id}`)
    return response.data
  }

  // Studios
  async getStudios(params?: FilterParams): Promise<PaginatedResponse<Studio>> {
    const response = await api.get('/studios', { params })
    return response.data
  }

  async getStudio(id: number): Promise<Studio> {
    const response = await api.get(`/studios/${id}`)
    return response.data
  }

  // Analysis
  async getAnalysisPlans(): Promise<AnalysisPlan[]> {
    const response = await api.get('/analysis/plans')
    return response.data
  }

  async getAnalysisPlan(id: number): Promise<AnalysisPlan> {
    const response = await api.get(`/analysis/plans/${id}`)
    return response.data
  }

  async createAnalysisPlan(data: Partial<AnalysisPlan>): Promise<AnalysisPlan> {
    const response = await api.post('/analysis/plans', data)
    return response.data
  }

  async updateAnalysisPlan(id: number, data: Partial<AnalysisPlan>): Promise<AnalysisPlan> {
    const response = await api.put(`/analysis/plans/${id}`, data)
    return response.data
  }

  async deleteAnalysisPlan(id: number): Promise<void> {
    await api.delete(`/analysis/plans/${id}`)
  }

  async analyzeMultipleScenes(sceneIds: number[], planId?: number): Promise<Job[]> {
    const response = await api.post('/analysis/batch', {
      scene_ids: sceneIds,
      plan_id: planId,
    })
    return response.data
  }

  async getAnalysisResults(sceneId: number): Promise<AnalysisResult[]> {
    const response = await api.get(`/analysis/results/${sceneId}`)
    return response.data
  }

  // Jobs
  async getJobs(params?: FilterParams): Promise<PaginatedResponse<Job>> {
    const response = await api.get('/jobs', { params })
    return response.data
  }

  async getJob(id: string): Promise<Job> {
    const response = await api.get(`/jobs/${id}`)
    return response.data
  }

  async cancelJob(id: string): Promise<void> {
    await api.post(`/jobs/${id}/cancel`)
  }

  async retryJob(id: string): Promise<Job> {
    const response = await api.post(`/jobs/${id}/retry`)
    return response.data
  }

  // Settings
  async getSettings(): Promise<Settings> {
    const response = await api.get('/settings')
    return response.data
  }

  async updateSetting(key: string, value: any): Promise<void> {
    await api.put('/settings', { [key]: value })
  }

  async testStashConnection(): Promise<{ success: boolean; message: string }> {
    const response = await api.post('/settings/test-connection')
    return response.data
  }

  // Sync
  async getSyncStatus(): Promise<SyncStatus> {
    const response = await api.get('/sync/status')
    return response.data
  }

  async startSync(): Promise<Job> {
    const response = await api.post('/sync/start')
    return response.data
  }

  async stopSync(): Promise<void> {
    await api.post('/sync/stop')
  }

  async getSyncHistory(params?: FilterParams): Promise<PaginatedResponse<Job>> {
    const response = await api.get('/sync/history', { params })
    return response.data
  }
}

export const apiClient = new ApiClient()
export default apiClient