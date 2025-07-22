const apiClient = {
  // Scenes
  getScenes: jest.fn().mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    per_page: 50,
    total_pages: 0,
  }),
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
  updateAnalysisPlan: jest.fn(),
  deleteAnalysisPlan: jest.fn(),
  cancelAnalysisPlan: jest.fn(),
  bulkUpdateAnalysisPlan: jest.fn(),
  analyzeMultipleScenes: jest.fn(),
  analyzeScenes: jest.fn(),
  getAnalysisResults: jest.fn(),
  getAnalysisStats: jest.fn(),

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
    summary: {
      scene_count: 0,
      performer_count: 0,
      tag_count: 0,
      studio_count: 0,
    },
    sync: {
      last_scene_sync: undefined,
      last_performer_sync: undefined,
      last_tag_sync: undefined,
      last_studio_sync: undefined,
      pending_scenes: 0,
      is_syncing: false,
    },
    analysis: {
      scenes_not_analyzed: 0,
      scenes_not_video_analyzed: 0,
      draft_plans: 0,
      reviewing_plans: 0,
      is_analyzing: false,
    },
    organization: {
      unorganized_scenes: 0,
    },
    metadata: {
      scenes_without_files: 0,
      scenes_missing_details: 0,
      scenes_without_studio: 0,
      scenes_without_performers: 0,
      scenes_without_tags: 0,
    },
    jobs: {
      recent_failed_jobs: 0,
      running_jobs: [],
      completed_jobs: [],
    },
    actionable_items: [],
  }),
  startSync: jest.fn(),
  stopSync: jest.fn(),
  getSyncHistory: jest.fn(),
};

export { apiClient };
export default apiClient;
