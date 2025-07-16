import { useState, useEffect } from 'react';
import { message } from 'antd';
import api from '@/services/api';
import {
  Schedule,
  ScheduleRun,
  CreateScheduleData,
  UpdateScheduleData,
  ScheduleStats,
} from '../types';

export function useSchedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSchedules = async () => {
    try {
      setLoading(true);
      const response = await api.get('/schedules');
      setSchedules(response.data.schedules || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      void message.error('Failed to fetch schedules');
    } finally {
      setLoading(false);
    }
  };

  const createSchedule = async (data: CreateScheduleData) => {
    try {
      const response = await api.post('/schedules', data);
      const newSchedule = response.data;
      setSchedules((prev) => [...prev, newSchedule]);
      void message.success('Schedule created successfully');
      return newSchedule;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      void message.error(errorMessage);
      throw err;
    }
  };

  const updateSchedule = async (id: number, data: UpdateScheduleData) => {
    try {
      const response = await api.put(`/schedules/${id}`, data);
      const updatedSchedule = response.data;
      setSchedules((prev) =>
        prev.map((s) => (s.id === id ? updatedSchedule : s))
      );
      void message.success('Schedule updated successfully');
      return updatedSchedule;
    } catch (err) {
      void message.error('Failed to update schedule');
      throw err;
    }
  };

  const deleteSchedule = async (id: number) => {
    try {
      await api.delete(`/schedules/${id}`);
      setSchedules((prev) => prev.filter((s) => s.id !== id));
      void message.success('Schedule deleted successfully');
    } catch (err) {
      void message.error('Failed to delete schedule');
      throw err;
    }
  };

  const toggleSchedule = async (id: number, enabled: boolean) => {
    return updateSchedule(id, { enabled });
  };

  const runScheduleNow = async (id: number) => {
    try {
      const response = await api.post(`/schedules/${id}/run`);
      void message.success('Schedule triggered successfully');
      return response.data;
    } catch (err) {
      void message.error('Failed to trigger schedule');
      throw err;
    }
  };

  useEffect(() => {
    void fetchSchedules();
  }, []);

  return {
    schedules,
    loading,
    error,
    refetch: fetchSchedules,
    createSchedule,
    updateSchedule,
    deleteSchedule,
    toggleSchedule,
    runScheduleNow,
  };
}

export function useScheduleHistory(scheduleId?: number) {
  const [runs, setRuns] = useState<ScheduleRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<ScheduleStats | null>(null);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const url = scheduleId
        ? `/schedules/${scheduleId}/runs`
        : '/schedule-runs';

      const response = await api.get(url);
      const data = response.data;
      setRuns(data.runs || []);
      setStats(data.stats || null);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchHistory();

    // Poll for updates every 5 seconds if there are running tasks
    const interval = setInterval(() => {
      if (runs.some((run) => run.status === 'running')) {
        void fetchHistory();
      }
    }, 5000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scheduleId]); // fetchHistory is stable and runs dependency would cause unnecessary re-renders

  return {
    runs,
    loading,
    error,
    stats,
    refetch: fetchHistory,
  };
}

export function useNextRuns(expression: string, count: number = 5) {
  const [nextRuns, setNextRuns] = useState<Date[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNextRuns = async () => {
    if (!expression) {
      setNextRuns([]);
      return;
    }

    try {
      setLoading(true);
      const response = await api.post('/schedules/preview', {
        expression,
        count,
      });
      const data = response.data;
      setNextRuns(data.next_runs.map((run: string) => new Date(run)));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid expression');
      setNextRuns([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      void fetchNextRuns();
    }, 500);

    return () => clearTimeout(debounceTimer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expression, count]); // fetchNextRuns is stable

  return { nextRuns, loading, error };
}
