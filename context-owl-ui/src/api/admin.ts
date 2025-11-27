/**
 * Admin API for cost monitoring and cache management
 */

import { apiClient } from './client';

// Types for API responses
export interface CostSummary {
  month_to_date: number;
  projected_monthly: number;
  days_elapsed: number;
  total_calls: number;
  cached_calls: number;
  cache_hit_rate_percent: number;
  breakdown_by_operation: Record<string, {
    cost: number;
    calls: number;
    cached_calls: number;
    input_tokens: number;
    output_tokens: number;
  }>;
}

export interface DailyCost {
  date: string;
  total_cost: number;
  total_calls: number;
  cached_calls: number;
  cache_hit_rate: number;
  operations: Record<string, {
    cost: number;
    calls: number;
  }>;
}

export interface DailyCostsResponse {
  days_requested: number;
  daily_costs: DailyCost[];
  total_cost: number;
}

export interface ModelCost {
  model: string;
  total_cost: number;
  total_calls: number;
  cached_calls: number;
  cache_hit_rate_percent: number;
  input_tokens: number;
  output_tokens: number;
  avg_cost_per_call: number;
}

export interface ModelCostsResponse {
  period_days: number;
  models: ModelCost[];
  total_cost: number;
}

export interface CacheStats {
  cache_entries: {
    total: number;
    active: number;
    expired: number;
  };
  performance: {
    cache_hits: number;
    cache_misses: number;
    total_requests: number;
    hit_rate_percent: number;
  };
}

export interface SourceStats {
  source: string;
  total_articles: number;
  llm_extractions: number;
  simple_extractions: number;
  llm_percentage: number;
}

export interface ProcessingStatsResponse {
  period_days: number;
  sources: SourceStats[];
  summary: {
    total_articles: number;
    total_llm_extractions: number;
    total_simple_extractions: number;
  };
}

export interface ClearCacheResponse {
  deleted_count: number;
  message: string;
}

export const adminAPI = {
  /**
   * Get monthly cost summary with projections
   */
  getCostSummary: () => 
    apiClient.get<CostSummary>('/admin/api-costs/summary'),

  /**
   * Get daily cost breakdown
   */
  getDailyCosts: (days: number = 7) =>
    apiClient.get<DailyCostsResponse>('/admin/api-costs/daily', { days }),

  /**
   * Get cost breakdown by model
   */
  getCostsByModel: (days: number = 30) =>
    apiClient.get<ModelCostsResponse>('/admin/api-costs/by-model', { days }),

  /**
   * Get cache performance statistics
   */
  getCacheStats: () =>
    apiClient.get<CacheStats>('/admin/cache/stats'),

  /**
   * Get article processing statistics (LLM vs regex)
   */
  getProcessingStats: (days: number = 7) =>
    apiClient.get<ProcessingStatsResponse>('/admin/processing/stats', { days }),

  /**
   * Clear expired cache entries
   */
  clearExpiredCache: () =>
    apiClient.post<ClearCacheResponse>('/admin/cache/clear-expired'),
};
