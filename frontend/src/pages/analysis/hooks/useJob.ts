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
        return response;
      } catch (err) {
        console.error('Failed to fetch job:', err);
        setError('Failed to fetch job details');
        setJob(null);
        return null;
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch
    void fetchJob();

    // Poll for updates if job is running
    const interval = setInterval(() => {
      void (async () => {
        try {
          const currentJob = await apiClient.getJob(jobId);
          if (
            currentJob &&
            (currentJob.status === 'running' || currentJob.status === 'pending')
          ) {
            void fetchJob();
          }
        } catch {
          // Ignore errors in polling
        }
      })();
    }, 2000);

    return () => {
      clearInterval(interval);
    };
  }, [jobId]);

  return { job, loading, error };
};
