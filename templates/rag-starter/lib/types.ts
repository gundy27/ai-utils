// API Types matching the backend models

export interface DocumentIngestResponse {
  document_id: string;
  chunks_created: number;
  vectors_stored: number;
  total_tokens: number;
  estimated_cost_usd: number;
  processing_time_ms: number;
}

export interface SourceChunk {
  chunk_id: string;
  score: number;
  text?: string;
}

export interface ChatResponse {
  answer: string;
  session_id: string;
  sources: SourceChunk[];
  model: string;
  tokens_used: number;
  cost_usd: number;
  processing_time_ms: number;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  score: number;
  text?: string;
  metadata: Record<string, any>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  processing_time_ms: number;
}

export interface Stats {
  vector_count: number;
  parsers_registered: number;
  supported_file_types: string[];
  chunk_max_tokens: number;
  embedding_model: string;
  embedding_dimensions: number;
}

export type ViewType = "chat" | "documents" | "system";

export interface Settings {
  model: string;
  topK: number;
  chunkMaxTokens: number;
  userId: string;
  useStreaming: boolean;
}

export interface HealthStatus {
  api: boolean;
  vectorStore: boolean;
  parsers: boolean;
  embeddings: boolean;
}

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceChunk[];
  tokens?: number;
  cost?: number;
}

export interface Session {
  id: string;
  messages: Message[];
  created_at?: string;
  message_count?: number;
}
