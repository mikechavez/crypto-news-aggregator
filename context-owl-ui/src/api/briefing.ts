import { apiClient } from './client';
import type { BriefingResponse } from '../types';

export const briefingAPI = {
  /**
   * Get the latest briefing (morning or evening, whichever is most recent)
   */
  getLatest: async (): Promise<BriefingResponse> => {
    return apiClient.get<BriefingResponse>('/api/v1/briefing');
  },

  /**
   * Get morning briefing for a specific date
   * @param date - Optional date in YYYY-MM-DD format (defaults to today)
   */
  getMorning: async (date?: string): Promise<BriefingResponse> => {
    return apiClient.get<BriefingResponse>('/api/v1/briefing/morning', date ? { date } : undefined);
  },

  /**
   * Get evening briefing for a specific date
   * @param date - Optional date in YYYY-MM-DD format (defaults to today)
   */
  getEvening: async (date?: string): Promise<BriefingResponse> => {
    return apiClient.get<BriefingResponse>('/api/v1/briefing/evening', date ? { date } : undefined);
  },
};
