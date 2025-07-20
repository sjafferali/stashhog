import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { useWebSocket } from './useWebSocket';

interface Job {
  id: string;
  job_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  created_at: string;
  updated_at: string;
}

interface UseRunningJobsReturn {
  runningJobs: Job[];
  runningCount: number;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export const useRunningJobs = (): UseRunningJobsReturn => {
  const [runningJobs, setRunningJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lastMessage } = useWebSocket('/api/jobs/ws');

  const fetchRunningJobs = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('/api/jobs', {
        params: {
          status: ['pending', 'running'],
        },
      });

      const jobs = response.data.jobs || [];
      setRunningJobs(
        jobs.filter(
          (job: Job) => job.status === 'pending' || job.status === 'running'
        )
      );
      setError(null);
    } catch (err) {
      console.error('Failed to fetch running jobs:', err);
      setError('Failed to fetch running jobs');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    void fetchRunningJobs();
  }, [fetchRunningJobs]);

  // Handle WebSocket updates
  useEffect(() => {
    if (lastMessage && typeof lastMessage === 'object') {
      const update = lastMessage as { type: string; job: Job };

      if (update.type === 'job_update' && update.job) {
        setRunningJobs((prevJobs) => {
          const jobIndex = prevJobs.findIndex((j) => j.id === update.job.id);

          // If job is completed, failed, or cancelled, remove it
          if (
            ['completed', 'failed', 'cancelled'].includes(update.job.status)
          ) {
            return prevJobs.filter((j) => j.id !== update.job.id);
          }

          // If job is running or pending
          if (['pending', 'running'].includes(update.job.status)) {
            if (jobIndex >= 0) {
              // Update existing job
              const newJobs = [...prevJobs];
              newJobs[jobIndex] = update.job;
              return newJobs;
            } else {
              // Add new job
              return [...prevJobs, update.job];
            }
          }

          return prevJobs;
        });
      }
    }
  }, [lastMessage]);

  // Auto-refetch every 30 seconds as fallback
  useEffect(() => {
    const interval = setInterval(() => {
      void fetchRunningJobs();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchRunningJobs]);

  return {
    runningJobs,
    runningCount: runningJobs.length,
    isLoading,
    error,
    refetch: () => {
      void fetchRunningJobs();
    },
  };
};
