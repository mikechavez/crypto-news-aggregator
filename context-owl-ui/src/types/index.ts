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
  entity: string;              // Entity name (e.g., "Solana")
  entity_type: string;         // Type (e.g., "cryptocurrency")
  signal_score: number;        // Overall signal strength
  velocity: number;            // Mentions per hour
  source_count: number;        // Number of sources
  sentiment: number;           // Sentiment score (-1 to 1)
  first_seen: string;          // ISO timestamp
  last_updated: string;        // ISO timestamp
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
  theme: string;              // Short title for the narrative
  entities: string[];         // List of entities in this narrative
  story: string;              // 1-2 sentence summary of the narrative
  article_count: number;      // Number of articles supporting this narrative
  updated_at: string;         // ISO timestamp of last update
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

// Backend returns array directly, not wrapped in object
export type NarrativesResponse = Narrative[];

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
  limit?: number;
  offset?: number;
}
