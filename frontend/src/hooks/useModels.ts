import { useState, useEffect } from 'react';
import api from '@/services/api';
import type { ModelsResponse } from '@/types/models';

export interface UseModelsReturn {
  models: ModelsResponse | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

export function useModels(): UseModelsReturn {
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchModels = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/analysis/models');
      setModels(response.data);
    } catch (err) {
      setError(err as Error);
      console.error('Failed to fetch models:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchModels();
  }, []);

  return {
    models,
    loading,
    error,
    refresh: fetchModels,
  };
}
