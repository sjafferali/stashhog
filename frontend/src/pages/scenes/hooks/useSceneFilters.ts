import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SceneQueryParams } from './useScenes';

export type SceneFilters = Omit<
  SceneQueryParams,
  'page' | 'per_page' | 'sort_by' | 'sort_order'
> & {
  exclude_tag_ids?: string[];
};

const DEFAULT_FILTERS: SceneFilters = {
  search: '',
  scene_ids: [],
  performer_ids: [],
  tag_ids: [],
  exclude_tag_ids: [],
  studio_id: undefined,
  organized: undefined,
  analyzed: undefined,
  video_analyzed: undefined,
  has_active_jobs: undefined,
  date_from: '',
  date_to: '',
};

export function useSceneFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse filters from URL
  const filters = useMemo<SceneFilters>(() => {
    const params: SceneFilters = { ...DEFAULT_FILTERS };

    // String filters
    params.search = searchParams.get('search') || '';
    params.date_from = searchParams.get('date_from') || '';
    params.date_to = searchParams.get('date_to') || '';

    // Boolean filters
    const organized = searchParams.get('organized');
    if (organized !== null) {
      params.organized = organized === 'true';
    }

    const analyzed = searchParams.get('analyzed');
    if (analyzed !== null) {
      params.analyzed = analyzed === 'true';
    }

    const videoAnalyzed = searchParams.get('video_analyzed');
    if (videoAnalyzed !== null) {
      params.video_analyzed = videoAnalyzed === 'true';
    }

    const hasActiveJobs = searchParams.get('has_active_jobs');
    if (hasActiveJobs !== null) {
      params.has_active_jobs = hasActiveJobs === 'true';
    }

    // Array filters (comma-separated IDs)
    const sceneIds = searchParams.get('scene_ids');
    if (sceneIds) {
      params.scene_ids = sceneIds.split(',').filter(Boolean);
    }

    const performerIds = searchParams.get('performer_ids');
    if (performerIds) {
      params.performer_ids = performerIds.split(',').filter(Boolean);
    }

    const tagIds = searchParams.get('tag_ids');
    if (tagIds) {
      params.tag_ids = tagIds.split(',').filter(Boolean);
    }

    const excludeTagIds = searchParams.get('exclude_tag_ids');
    if (excludeTagIds) {
      params.exclude_tag_ids = excludeTagIds.split(',').filter(Boolean);
    }

    // Single studio ID
    const studioId = searchParams.get('studio_id');
    if (studioId) {
      params.studio_id = studioId;
    }

    return params;
  }, [searchParams]);

  // Update a single filter
  const updateFilter = (
    key: keyof SceneFilters,
    value: string | number | boolean | string[] | undefined
  ) => {
    const newParams = new URLSearchParams(searchParams);

    if (
      value === undefined ||
      value === null ||
      value === '' ||
      (Array.isArray(value) && value.length === 0)
    ) {
      // Remove empty values
      newParams.delete(key as string);
    } else if (Array.isArray(value)) {
      // Handle array values
      newParams.set(key as string, value.join(','));
    } else if (typeof value === 'boolean') {
      // Handle boolean values
      newParams.set(key as string, value.toString());
    } else {
      // Handle other values
      newParams.set(key as string, value.toString());
    }

    setSearchParams(newParams);
  };

  // Update multiple filters at once
  const updateFilters = (updates: Partial<SceneFilters>) => {
    const newParams = new URLSearchParams(searchParams);

    Object.entries(updates).forEach(([key, value]) => {
      if (
        value === undefined ||
        value === null ||
        value === '' ||
        (Array.isArray(value) && value.length === 0)
      ) {
        newParams.delete(key);
      } else if (Array.isArray(value)) {
        newParams.set(key, value.join(','));
      } else if (typeof value === 'boolean') {
        newParams.set(key, value.toString());
      } else {
        newParams.set(key, value.toString());
      }
    });

    setSearchParams(newParams);
  };

  // Reset all filters
  const resetFilters = () => {
    const newParams = new URLSearchParams();
    // Preserve pagination/sort params if they exist
    ['page', 'per_page', 'sort_by', 'sort_order'].forEach((key) => {
      const value = searchParams.get(key);
      if (value) {
        newParams.set(key, value);
      }
    });
    setSearchParams(newParams);
  };

  // Get active filter count
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.search) count++;
    if (
      filters.scene_ids &&
      Array.isArray(filters.scene_ids) &&
      filters.scene_ids.length > 0
    )
      count++;
    if (
      filters.performer_ids &&
      Array.isArray(filters.performer_ids) &&
      filters.performer_ids.length > 0
    )
      count++;
    if (
      filters.tag_ids &&
      Array.isArray(filters.tag_ids) &&
      filters.tag_ids.length > 0
    )
      count++;
    if (
      filters.exclude_tag_ids &&
      Array.isArray(filters.exclude_tag_ids) &&
      filters.exclude_tag_ids.length > 0
    )
      count++;
    if (filters.studio_id) count++;
    if (filters.organized !== undefined) count++;
    if (filters.analyzed !== undefined) count++;
    if (filters.video_analyzed !== undefined) count++;
    if (filters.date_from) count++;
    if (filters.date_to) count++;
    return count;
  }, [filters]);

  // Check if any filters are active
  const hasActiveFilters = activeFilterCount > 0;

  return {
    filters,
    updateFilter,
    updateFilters,
    resetFilters,
    activeFilterCount,
    hasActiveFilters,
  };
}
