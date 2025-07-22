import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SyncManagement from './SyncManagement';
import apiClient from '@/services/apiClient';
import api from '@/services/api';

// Mock the API client
jest.mock('@/services/apiClient');
jest.mock('@/services/api');

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;
const mockApi = api as jest.Mocked<typeof api>;

describe('SyncManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Mock the sync history API call
    mockApi.get.mockResolvedValue({ data: [] });
  });

  afterEach(() => {
    // Clean up any pending timers
    jest.clearAllTimers();
  });

  it('renders sync management title', () => {
    // Mock the API response
    mockApiClient.getSyncStatus.mockResolvedValue({
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
    });

    render(
      <MemoryRouter>
        <SyncManagement />
      </MemoryRouter>
    );

    expect(screen.getByText('Sync Management')).toBeInTheDocument();
  });

  it('displays sync idle status by default', () => {
    mockApiClient.getSyncStatus.mockResolvedValue({
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
    });

    render(
      <MemoryRouter>
        <SyncManagement />
      </MemoryRouter>
    );

    expect(screen.getByText('Sync is idle')).toBeInTheDocument();
  });

  it('displays statistics after loading', async () => {
    // Mock the API response
    mockApiClient.getSyncStatus.mockResolvedValue({
      summary: {
        scene_count: 100,
        performer_count: 50,
        tag_count: 75,
        studio_count: 10,
      },
      sync: {
        last_scene_sync: '2024-01-01T00:00:00Z',
        last_performer_sync: undefined,
        last_tag_sync: undefined,
        last_studio_sync: undefined,
        pending_scenes: 5,
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
    });

    render(
      <MemoryRouter>
        <SyncManagement />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('100')).toBeInTheDocument(); // scenes
      expect(screen.getByText('50')).toBeInTheDocument(); // performers
      expect(screen.getByText('75')).toBeInTheDocument(); // tags
      expect(screen.getByText('10')).toBeInTheDocument(); // studios
    });
  });

  it('displays last sync time', async () => {
    mockApiClient.getSyncStatus.mockResolvedValue({
      summary: {
        scene_count: 100,
        performer_count: 50,
        tag_count: 75,
        studio_count: 10,
      },
      sync: {
        last_scene_sync: '2024-01-01T00:00:00Z',
        last_performer_sync: undefined,
        last_tag_sync: undefined,
        last_studio_sync: undefined,
        pending_scenes: 5,
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
    });

    render(
      <MemoryRouter>
        <SyncManagement />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Last scene sync:/)).toBeInTheDocument();
      expect(screen.getByText(/Pending scenes: 5/)).toBeInTheDocument();
    });
  });

  it('handles start sync button click', async () => {
    mockApiClient.getSyncStatus.mockResolvedValue({
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
    });

    mockApiClient.startSync.mockResolvedValue({
      id: 'test-job-id',
      type: 'sync_all',
      status: 'running',
      progress: 0,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    });

    render(
      <MemoryRouter>
        <SyncManagement />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Start Sync')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Start Sync'));

    await waitFor(() => {
      expect(mockApiClient.startSync).toHaveBeenCalled();
    });
  });

  it('handles refresh button click', async () => {
    mockApiClient.getSyncStatus.mockResolvedValue({
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
    });

    render(
      <MemoryRouter>
        <SyncManagement />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument();
    });

    // Clear the initial call
    mockApiClient.getSyncStatus.mockClear();

    fireEvent.click(screen.getByText('Refresh'));

    await waitFor(() => {
      expect(mockApiClient.getSyncStatus).toHaveBeenCalled();
    });
  });

  it('handles API errors gracefully', async () => {
    // Mock the API to reject
    mockApiClient.getSyncStatus.mockRejectedValue(new Error('API Error'));

    // Suppress console.error for this test
    const consoleSpy = jest
      .spyOn(console, 'error')
      .mockImplementation(() => {});

    render(
      <MemoryRouter>
        <SyncManagement />
      </MemoryRouter>
    );

    await waitFor(() => {
      // Should display 0 values when error occurs
      expect(screen.getAllByText('0')).toHaveLength(4);
    });

    consoleSpy.mockRestore();
  });

  it('cleans up interval when component unmounts during sync', () => {
    jest.useFakeTimers();
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');

    // Mock syncing state
    mockApiClient.getSyncStatus.mockResolvedValue({
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
        is_syncing: true,
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
    });

    const { unmount } = render(
      <MemoryRouter>
        <SyncManagement />
      </MemoryRouter>
    );

    // Unmount the component
    unmount();

    // Check that cleanup happened
    expect(clearIntervalSpy).toHaveBeenCalled();

    clearIntervalSpy.mockRestore();
    jest.useRealTimers();
  });
});
