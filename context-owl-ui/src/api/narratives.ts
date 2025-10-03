import { apiClient } from './client';
import type { NarrativesResponse, Narrative } from '../types';

export const narrativesAPI = {
  getNarratives: async (): Promise<NarrativesResponse> => {
    return apiClient.get<NarrativesResponse>('/api/v1/narratives/active');
  },

  getNarrativeById: async (id: number): Promise<Narrative> => {
    return apiClient.get<Narrative>(`/api/v1/narratives/${id}`);
  },
};
