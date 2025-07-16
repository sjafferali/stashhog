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
  });

  it('renders dashboard title', () => {
    // Mock the API response
    mockApiClient.getSyncStatus.mockResolvedValue({
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
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
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
      scene_count: 100,
      performer_count: 50,
      tag_count: 75,
      studio_count: 10,
      last_scene_sync: '2024-01-01T00:00:00Z',
      last_performer_sync: undefined,
      last_tag_sync: undefined,
      last_studio_sync: undefined,
      pending_scenes: 5,
      pending_performers: 0,
      pending_tags: 0,
      pending_studios: 0,
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

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      // Should display 0 values when error occurs
      expect(screen.getAllByText('0')).toHaveLength(4);
    });

    consoleSpy.mockRestore();
  });
});
