import { useState, useEffect } from 'react';
import { Job } from '@/types/models';
import { apiClient } from '@/services/apiClient';

export const useJob = (jobId: string | null | undefined) => {
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      return;
    }

    const fetchJob = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiClient.getJob(jobId);
        setJob(response);
      } catch (err) {
        console.error('Failed to fetch job:', err);
        setError('Failed to fetch job details');
        setJob(null);
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch
    void fetchJob();

    // Poll for updates if job is running
    const interval = setInterval(() => {
      if (job && (job.status === 'running' || job.status === 'pending')) {
        void fetchJob();
      }
    }, 2000);

    return () => {
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]); // Don't include job in dependencies to avoid re-polling issues

  return { job, loading, error };
};
