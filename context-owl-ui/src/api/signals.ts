import { apiClient } from './client';
import type { SignalsResponse, Signal, SignalFilters } from '../types';

export const signalsAPI = {
  getSignals: async (filters?: SignalFilters): Promise<SignalsResponse> => {
    return apiClient.get<SignalsResponse>('/api/v1/signals/trending', filters);
  },

  getSignalById: async (id: number): Promise<Signal> => {
    return apiClient.get<Signal>(`/api/v1/signals/${id}`);
  },

  getSignalsByEntity: async (entityId: number, filters?: Omit<SignalFilters, 'entity_id'>): Promise<SignalsResponse> => {
    return apiClient.get<SignalsResponse>('/api/v1/signals/trending', {
      entity_id: entityId,
      ...filters,
    });
  },
};
