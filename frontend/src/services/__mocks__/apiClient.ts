const apiClient = {
  // Scenes
  getScenes: jest.fn(),
  getScene: jest.fn(),
  updateScene: jest.fn(),
  analyzeScene: jest.fn(),

  // Performers
  getPerformers: jest.fn(),
  getPerformer: jest.fn(),

  // Tags
  getTags: jest.fn(),
  getTag: jest.fn(),

  // Studios
  getStudios: jest.fn(),
  getStudio: jest.fn(),

  // Analysis
  getAnalysisPlans: jest.fn(),
  getAnalysisPlan: jest.fn(),
  createAnalysisPlan: jest.fn(),
  updateAnalysisPlan: jest.fn(),
  deleteAnalysisPlan: jest.fn(),
  analyzeMultipleScenes: jest.fn(),
  getAnalysisResults: jest.fn(),

  // Jobs
  getJobs: jest.fn(),
  getJob: jest.fn(),
  cancelJob: jest.fn(),
  retryJob: jest.fn(),

  // Settings
  getSettings: jest.fn(),
  updateSetting: jest.fn(),
  testStashConnection: jest.fn(),

  // Sync
  getSyncStatus: jest.fn().mockResolvedValue({
    scene_count: 0,
    performer_count: 0,
    tag_count: 0,
    studio_count: 0,
    last_scene_sync: undefined,
    last_performer_sync: undefined,
    last_tag_sync: undefined,
    last_studio_sync: undefined,
    pending_scenes: 0,
    pending_performers: 0,
    pending_tags: 0,
    pending_studios: 0,
  }),
  startSync: jest.fn(),
  stopSync: jest.fn(),
  getSyncHistory: jest.fn(),
};

export { apiClient };
export default apiClient;
