import { apiClient } from './client';

export interface ArticleEntity {
  name: string;
  type: string;
}

export interface Article {
  id: string;
  title: string;
  url: string;
  source: string;
  published_at: string;
  entities: ArticleEntity[];
}

export interface RecentArticlesResponse {
  articles: Article[];
  total: number;
}

export const articlesAPI = {
  getRecent: async (limit: number = 100): Promise<RecentArticlesResponse> => {
    return apiClient.get<RecentArticlesResponse>('/api/v1/articles/recent', { limit });
  },
};
