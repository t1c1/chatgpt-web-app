export interface SearchResult {
  message_id: string;
  conversation_id: string;
  title: string;
  provider: string;
  role: string;
  content: string;
  timestamp?: string;
  word_count: number;
  relevance_score: number;
  context?: Array<{ [key: string]: any }>;
}

export interface SearchResponse {
  query: string;
  mode: string;
  results: SearchResult[];
  total: number;
  execution_time_ms: number;
  filters_applied: { [key: string]: any };
}

export interface SearchRequest {
  query: string;
  mode?: string;
  limit?: number;
  offset?: number;
  project_id?: string;
  provider?: string;
  role?: string;
  date_from?: string;
  date_to?: string;
  alpha?: number;
  threshold?: number;
  include_context?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  provider: string;
  message_count: number;
  word_count: number;
  first_message_date?: string;
  last_message_date?: string;
  project_id?: string;
}
