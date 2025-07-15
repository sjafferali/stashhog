import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SceneQueryParams } from './useScenes';

export type SceneFilters = Omit<
  SceneQueryParams,
  'page' | 'size' | 'sort_by' | 'sort_dir'
>;

const DEFAULT_FILTERS: SceneFilters = {
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

export function useSceneFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse filters from URL
  const filters = useMemo<SceneFilters>(() => {
    const params: SceneFilters = { ...DEFAULT_FILTERS };

    // String filters
    params.search = searchParams.get('search') || '';
    params.path_contains = searchParams.get('path_contains') || '';
    params.date_from = searchParams.get('date_from') || '';
    params.date_to = searchParams.get('date_to') || '';

    // Boolean filters
    const organized = searchParams.get('organized');
    if (organized !== null) {
      params.organized = organized === 'true';
    }

    const hasDetails = searchParams.get('has_details');
    if (hasDetails !== null) {
      params.has_details = hasDetails === 'true';
    }

    // Array filters (comma-separated IDs)
    const performers = searchParams.get('performers');
    if (performers) {
      params.performers = performers.split(',').filter(Boolean);
    }

    const tags = searchParams.get('tags');
    if (tags) {
      params.tags = tags.split(',').filter(Boolean);
    }

    const studios = searchParams.get('studios');
    if (studios) {
      params.studios = studios.split(',').filter(Boolean);
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
    ['page', 'size', 'sort_by', 'sort_dir'].forEach((key) => {
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
