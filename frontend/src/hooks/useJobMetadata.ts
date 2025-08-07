/**
 * React hook for managing job metadata.
 * Ensures metadata is loaded on app startup and provides access to job configuration.
 */

import { useEffect, useState } from 'react';
import {
  jobMetadataService,
  JobMetadataResponse,
} from '../services/jobMetadataService';

export interface UseJobMetadataResult {
  metadata: JobMetadataResponse | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

export function useJobMetadata(): UseJobMetadataResult {
  const [metadata, setMetadata] = useState<JobMetadataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const loadMetadata = async (forceRefresh = false) => {
    try {
      setLoading(true);
      setError(null);
      const data = await jobMetadataService.fetchMetadata(forceRefresh);
      setMetadata(data);
    } catch (err) {
      console.error('Failed to load job metadata:', err);
      setError(err as Error);
      // Even on error, the app can continue with static fallbacks
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Load metadata on mount
    void loadMetadata();
  }, []);

  const refresh = async () => {
    await loadMetadata(true);
  };

  return {
    metadata,
    loading,
    error,
    refresh,
  };
}

/**
 * Hook to get metadata for a specific job type.
 */
export function useJobType(jobType: string) {
  const { metadata, loading, error } = useJobMetadata();

  const jobMetadata = metadata?.job_types.find(
    (job) => job.value === jobType || job.schema_value === jobType
  );

  return {
    metadata: jobMetadata,
    loading,
    error,
  };
}
