import { useQuery } from 'react-query';
import api from '@/services/api';
import { Scene, PaginatedResponse, FilterParams } from '@/types/models';

export interface SceneQueryParams extends FilterParams {
  performer_ids?: string[];
  tag_ids?: string[];
  studio_id?: string;
  organized?: boolean;
  analyzed?: boolean;
  date_from?: string;
  date_to?: string;
}

export function useScenes(params: SceneQueryParams) {
  return useQuery<PaginatedResponse<Scene>, Error>({
    queryKey: ['scenes', params],
    queryFn: async () => {
      // Filter out empty date strings before sending to API
      const filteredParams = Object.entries(params).reduce(
        (acc, [key, value]) => {
          if ((key === 'date_from' || key === 'date_to') && value === '') {
            return acc;
          }
          return { ...acc, [key]: value };
        },
        {} as SceneQueryParams
      );

      const response = await api.get('/scenes', { params: filteredParams });
      return response.data;
    },
    keepPreviousData: true,
    staleTime: 30000, // Consider data stale after 30 seconds
    cacheTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  });
}

export function useScene(id: string | number) {
  return useQuery<Scene, Error>({
    queryKey: ['scene', id],
    queryFn: async () => {
      const response = await api.get(`/scenes/${id}`);
      return response.data;
    },
    enabled: !!id,
    staleTime: 60000, // Consider data stale after 1 minute
  });
}
