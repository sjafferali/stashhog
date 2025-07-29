import { SceneFilters } from '../hooks/useSceneFilters';
import { SceneQueryParams } from '../hooks/useScenes';

export function buildFilterQuery(filters: SceneFilters): URLSearchParams {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }

    if (Array.isArray(value) && value.length === 0) {
      return;
    }

    if (Array.isArray(value)) {
      params.set(key, value.join(','));
    } else if (typeof value === 'boolean') {
      params.set(key, value.toString());
    } else {
      params.set(key, value.toString());
    }
  });

  return params;
}

export function parseFilterQuery(params: URLSearchParams): SceneFilters {
  const filters: SceneFilters = {
    search: params.get('search') || '',
    scene_ids: [],
    performer_ids: [],
    tag_ids: [],
    exclude_tag_ids: [],
    studio_id: undefined,
    organized: undefined,
    analyzed: undefined,
    video_analyzed: undefined,
    date_from: params.get('date_from') || '',
    date_to: params.get('date_to') || '',
  };

  // Parse array values
  const sceneIds = params.get('scene_ids');
  if (sceneIds) {
    filters.scene_ids = sceneIds.split(',').filter(Boolean);
  }

  const performerIds = params.get('performer_ids');
  if (performerIds) {
    filters.performer_ids = performerIds.split(',').filter(Boolean);
  }

  const tagIds = params.get('tag_ids');
  if (tagIds) {
    filters.tag_ids = tagIds.split(',').filter(Boolean);
  }

  const excludeTagIds = params.get('exclude_tag_ids');
  if (excludeTagIds) {
    filters.exclude_tag_ids = excludeTagIds.split(',').filter(Boolean);
  }

  // Parse single studio ID
  const studioId = params.get('studio_id');
  if (studioId) {
    filters.studio_id = studioId;
  }

  // Parse boolean values
  const organized = params.get('organized');
  if (organized !== null) {
    filters.organized = organized === 'true';
  }

  const analyzed = params.get('analyzed');
  if (analyzed !== null) {
    filters.analyzed = analyzed === 'true';
  }

  const videoAnalyzed = params.get('video_analyzed');
  if (videoAnalyzed !== null) {
    filters.video_analyzed = videoAnalyzed === 'true';
  }

  return filters;
}

export function getActiveFilterCount(filters: SceneFilters): number {
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
}

export function getDefaultFilters(): SceneFilters {
  return {
    search: '',
    scene_ids: [],
    performer_ids: [],
    tag_ids: [],
    exclude_tag_ids: [],
    studio_id: undefined,
    organized: undefined,
    analyzed: undefined,
    video_analyzed: undefined,
    date_from: '',
    date_to: '',
  };
}

export function mergeWithQueryParams(
  filters: SceneFilters,
  queryParams: Partial<SceneQueryParams>
): SceneQueryParams {
  return {
    ...filters,
    ...queryParams,
    // Ensure arrays are properly merged
    scene_ids: Array.isArray(filters.scene_ids) ? filters.scene_ids : [],
    performer_ids: Array.isArray(filters.performer_ids)
      ? filters.performer_ids
      : [],
    tag_ids: Array.isArray(filters.tag_ids) ? filters.tag_ids : [],
    exclude_tag_ids: Array.isArray(filters.exclude_tag_ids)
      ? filters.exclude_tag_ids
      : [],
  };
}

// Helper to format filter display names
export function getFilterDisplayName(key: string | number): string {
  const displayNames: Record<string, string> = {
    search: 'Search',
    scene_ids: 'Scene IDs',
    performer_ids: 'Performers',
    tag_ids: 'Tags',
    exclude_tag_ids: 'Exclude Tags',
    studio_id: 'Studio',
    organized: 'Organized',
    analyzed: 'Analyzed',
    video_analyzed: 'Video Analyzed',
    date_from: 'Date From',
    date_to: 'Date To',
  };

  return displayNames[key as string] || String(key);
}

// Helper to check if a filter value is empty
export function isFilterEmpty(value: unknown): boolean {
  if (value === undefined || value === null || value === '') {
    return true;
  }
  if (Array.isArray(value) && value.length === 0) {
    return true;
  }
  return false;
}
