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

// Narrative summary for signals
export interface NarrativeSummary {
  id: string;                  // Narrative ObjectId
  title: string;               // Narrative title
  theme: string;               // Theme category
  lifecycle: string;           // Lifecycle stage
}

// Signal types
export interface Signal {
  entity: string;              // Entity name (e.g., "Solana")
  entity_type: string;         // Type (e.g., "cryptocurrency")
  signal_score: number;        // Overall signal strength
  velocity: number;            // Mentions per hour
  source_count: number;        // Number of sources
  sentiment: number;           // Sentiment score (-1 to 1)
  is_emerging: boolean;        // True if not part of any narrative
  narratives: NarrativeSummary[]; // Narratives containing this entity
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
  theme: string;              // Theme category (e.g., regulatory, defi_adoption)
  title: string;              // Generated narrative title
  summary: string;            // AI-generated narrative summary
  entities: string[];         // List of entities in this narrative
  article_count: number;      // Number of articles supporting this narrative
  mention_velocity: number;   // Articles per day rate
  lifecycle: string;          // Lifecycle stage: emerging, hot, mature, declining
  first_seen: string;         // ISO timestamp when narrative was first detected
  last_updated: string;       // ISO timestamp of last update
  // Backward compatibility fields
  updated_at?: string;        // Alias for last_updated
  story?: string;             // Alias for summary
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
