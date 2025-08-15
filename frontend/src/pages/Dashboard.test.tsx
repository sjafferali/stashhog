import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from './Dashboard';
import apiClient from '@/services/apiClient';

// Mock the API client
jest.mock('@/services/apiClient');

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('Dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Mock getRecentProcessedTorrents to return empty array by default
    mockApiClient.getRecentProcessedTorrents.mockResolvedValue({
      total: 0,
      torrents: [],
    });
  });

  it('renders dashboard title', async () => {
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
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });

  it('displays loading state initially', () => {
    // Mock the API to return a pending promise
    mockApiClient.getSyncStatus.mockReturnValue(new Promise(() => {}));

    const { container } = render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    // Check for Ant Design spin class
    expect(container.querySelector('.ant-spin')).toBeInTheDocument();
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
        scenes_not_analyzed: 20,
        scenes_not_video_analyzed: 80,
        draft_plans: 2,
        reviewing_plans: 1,
        is_analyzing: false,
      },
      organization: {
        unorganized_scenes: 15,
      },
      metadata: {
        scenes_without_files: 0,
        scenes_missing_details: 10,
        scenes_without_studio: 5,
        scenes_without_performers: 8,
        scenes_without_tags: 12,
      },
      jobs: {
        recent_failed_jobs: 0,
        running_jobs: [],
        completed_jobs: [],
      },
      actionable_items: [
        {
          id: 'pending_sync',
          type: 'sync',
          title: 'Pending Sync',
          description: '5 scenes have been updated in Stash since last sync',
          count: 5,
          action: 'sync_scenes',
          action_label: 'Run Incremental Sync',
          priority: 'medium',
          visible: true,
        },
      ],
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('100')).toBeInTheDocument(); // scenes
      expect(screen.getByText('50')).toBeInTheDocument(); // performers
      expect(screen.getByText('75')).toBeInTheDocument(); // tags
      expect(screen.getByText('10')).toBeInTheDocument(); // studios
    });
  });

  it('handles API errors gracefully', async () => {
    // Mock the API to reject
    mockApiClient.getSyncStatus.mockRejectedValue(new Error('API Error'));

    // Suppress console.error for this test
    const consoleSpy = jest
      .spyOn(console, 'error')
      .mockImplementation(() => {});

    const { container } = render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    // Wait for the loading state to complete
    await waitFor(() => {
      // When API fails, the dashboard should still render without crashing
      // The component stays in loading state, so we should see a spinner
      expect(container.querySelector('.ant-spin')).toBeInTheDocument();
    });

    consoleSpy.mockRestore();
  });
});
