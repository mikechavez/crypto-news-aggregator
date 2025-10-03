import { apiClient } from './client';
import type { Entity, EntityDetailResponse } from '../types';

export const entitiesAPI = {
  getEntityById: async (id: number): Promise<Entity> => {
    return apiClient.get<Entity>(`/api/v1/entities/${id}`);
  },

  getEntityDetail: async (id: number): Promise<EntityDetailResponse> => {
    return apiClient.get<EntityDetailResponse>(`/api/v1/entities/${id}/detail`);
  },

  searchEntities: async (query: string): Promise<Entity[]> => {
    return apiClient.get<Entity[]>('/api/v1/entities/search', { q: query });
  },
};
