import { apiClient } from './client';
import type { NarrativesResponse, Narrative } from '../types';

export const narrativesAPI = {
  getNarratives: async (): Promise<NarrativesResponse> => {
    return apiClient.get<NarrativesResponse>('/api/v1/narratives/active');
  },

  getNarrativeById: async (id: number): Promise<Narrative> => {
    return apiClient.get<Narrative>(`/api/v1/narratives/${id}`);
  },

  getArchivedNarratives: async (limit: number = 50, days: number = 30): Promise<NarrativesResponse> => {
    return apiClient.get<NarrativesResponse>(`/api/v1/narratives/archived?limit=${limit}&days=${days}`);
  },

  getResurrectedNarratives: async (limit: number = 20, days: number = 7): Promise<NarrativesResponse> => {
    return apiClient.get<NarrativesResponse>(`/api/v1/narratives/resurrections?limit=${limit}&days=${days}`);
  },
};
