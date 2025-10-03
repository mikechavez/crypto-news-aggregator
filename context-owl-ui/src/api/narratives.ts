import { apiClient } from './client';
import type { NarrativesResponse, Narrative, NarrativeFilters } from '../types';

export const narrativesAPI = {
  getNarratives: async (filters?: NarrativeFilters): Promise<NarrativesResponse> => {
    return apiClient.get<NarrativesResponse>('/api/v1/narratives/active', filters);
  },

  getNarrativeById: async (id: number): Promise<Narrative> => {
    return apiClient.get<Narrative>(`/api/v1/narratives/${id}`);
  },
};
