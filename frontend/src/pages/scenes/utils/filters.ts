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
    performers: [],
    tags: [],
    studios: [],
    organized: undefined,
    has_details: undefined,
    date_from: params.get('date_from') || '',
    date_to: params.get('date_to') || '',
    path_contains: params.get('path_contains') || '',
  };

  // Parse array values
  const performers = params.get('performers');
  if (performers) {
    filters.performers = performers.split(',').filter(Boolean);
  }

  const tags = params.get('tags');
  if (tags) {
    filters.tags = tags.split(',').filter(Boolean);
  }

  const studios = params.get('studios');
  if (studios) {
    filters.studios = studios.split(',').filter(Boolean);
  }

  // Parse boolean values
  const organized = params.get('organized');
  if (organized !== null) {
    filters.organized = organized === 'true';
  }

  const hasDetails = params.get('has_details');
  if (hasDetails !== null) {
    filters.has_details = hasDetails === 'true';
  }

  return filters;
}

export function getActiveFilterCount(filters: SceneFilters): number {
  let count = 0;

  if (filters.search) count++;
  if (
    filters.performers &&
    Array.isArray(filters.performers) &&
    filters.performers.length > 0
  )
    count++;
  if (filters.tags && Array.isArray(filters.tags) && filters.tags.length > 0)
    count++;
  if (
    filters.studios &&
    Array.isArray(filters.studios) &&
    filters.studios.length > 0
  )
    count++;
  if (filters.organized !== undefined) count++;
  if (filters.has_details !== undefined) count++;
  if (filters.date_from) count++;
  if (filters.date_to) count++;
  if (filters.path_contains) count++;

  return count;
}

export function getDefaultFilters(): SceneFilters {
  return {
    search: '',
    performers: [],
    tags: [],
    studios: [],
    organized: undefined,
    has_details: undefined,
    date_from: '',
    date_to: '',
    path_contains: '',
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
    performers: Array.isArray(filters.performers) ? filters.performers : [],
    tags: Array.isArray(filters.tags) ? filters.tags : [],
    studios: Array.isArray(filters.studios) ? filters.studios : [],
  };
}

// Helper to format filter display names
export function getFilterDisplayName(key: string | number): string {
  const displayNames: Record<string, string> = {
    search: 'Search',
    performers: 'Performers',
    tags: 'Tags',
    studios: 'Studios',
    organized: 'Organized',
    has_details: 'Has Details',
    date_from: 'Date From',
    date_to: 'Date To',
    path_contains: 'Path Contains',
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
