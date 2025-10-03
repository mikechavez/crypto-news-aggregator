// Core entity types
export interface Entity {
  id: number;
  name: string;
  entity_type: string;
  created_at: string;
}

export interface EntityMention {
  id: number;
  entity_id: number;
  article_id: number;
  mention_count: number;
  sentiment_score: number | null;
  created_at: string;
}

// Signal types
export interface Signal {
  id: number;
  entity_id: number;
  signal_type: string;
  strength: number;
  context: Record<string, any>;
  detected_at: string;
  entity?: Entity;
}

export interface SignalScore {
  id: number;
  entity_id: number;
  signal_type: string;
  score: number;
  metadata: Record<string, any>;
  created_at: string;
}

// Narrative types
export interface Narrative {
  id: number;
  title: string;
  description: string | null;
  keywords: string[];
  article_count: number;
  created_at: string;
  updated_at: string;
}

export interface NarrativeArticle {
  id: number;
  narrative_id: number;
  article_id: number;
  relevance_score: number;
  created_at: string;
}

// Article types
export interface Article {
  id: number;
  title: string;
  url: string;
  published_at: string;
  source: string;
  summary: string | null;
  sentiment_score: number | null;
  created_at: string;
}

// API response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SignalsResponse {
  signals: Signal[];
  total: number;
}

export interface NarrativesResponse {
  narratives: Narrative[];
  total: number;
}

export interface EntityDetailResponse {
  entity: Entity;
  mentions: EntityMention[];
  signals: Signal[];
  recent_articles: Article[];
}

// Filter and query types
export interface SignalFilters extends Record<string, string | number | boolean | undefined> {
  entity_id?: number;
  signal_type?: string;
  min_strength?: number;
  limit?: number;
  offset?: number;
}

export interface NarrativeFilters extends Record<string, string | number | boolean | string[] | undefined> {
  min_articles?: number;
  keywords?: string[];
  limit?: number;
  offset?: number;
}
