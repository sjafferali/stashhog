import { useState, useEffect } from 'react';
import { message } from 'antd';
import { Schedule, ScheduleRun, CreateScheduleData, UpdateScheduleData, ScheduleStats } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function useSchedules() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSchedules = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/schedules`, {
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch schedules');
      }
      
      const data = await response.json();
      setSchedules(data.schedules || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      message.error('Failed to fetch schedules');
    } finally {
      setLoading(false);
    }
  };

  const createSchedule = async (data: CreateScheduleData) => {
    try {
      const response = await fetch(`${API_BASE}/api/schedules`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create schedule');
      }
      
      const newSchedule = await response.json();
      setSchedules(prev => [...prev, newSchedule]);
      message.success('Schedule created successfully');
      return newSchedule;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      message.error(errorMessage);
      throw err;
    }
  };

  const updateSchedule = async (id: number, data: UpdateScheduleData) => {
    try {
      const response = await fetch(`${API_BASE}/api/schedules/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update schedule');
      }
      
      const updatedSchedule = await response.json();
      setSchedules(prev => prev.map(s => s.id === id ? updatedSchedule : s));
      message.success('Schedule updated successfully');
      return updatedSchedule;
    } catch (err) {
      message.error('Failed to update schedule');
      throw err;
    }
  };

  const deleteSchedule = async (id: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/schedules/${id}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete schedule');
      }
      
      setSchedules(prev => prev.filter(s => s.id !== id));
      message.success('Schedule deleted successfully');
    } catch (err) {
      message.error('Failed to delete schedule');
      throw err;
    }
  };

  const toggleSchedule = async (id: number, enabled: boolean) => {
    return updateSchedule(id, { enabled });
  };

  const runScheduleNow = async (id: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/schedules/${id}/run`, {
        method: 'POST',
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to trigger schedule');
      }
      
      const result = await response.json();
      message.success('Schedule triggered successfully');
      return result;
    } catch (err) {
      message.error('Failed to trigger schedule');
      throw err;
    }
  };

  useEffect(() => {
    fetchSchedules();
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
        ? `${API_BASE}/api/schedules/${scheduleId}/runs`
        : `${API_BASE}/api/schedule-runs`;
      
      const response = await fetch(url, {
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch schedule history');
      }
      
      const data = await response.json();
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
    fetchHistory();
    
    // Poll for updates every 5 seconds if there are running tasks
    const interval = setInterval(() => {
      if (runs.some(run => run.status === 'running')) {
        fetchHistory();
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [scheduleId]);

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
      const response = await fetch(`${API_BASE}/api/schedules/preview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ expression, count }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Invalid cron expression');
      }
      
      const data = await response.json();
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
      fetchNextRuns();
    }, 500);

    return () => clearTimeout(debounceTimer);
  }, [expression, count]);

  return { nextRuns, loading, error };
}