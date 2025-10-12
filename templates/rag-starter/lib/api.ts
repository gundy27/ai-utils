// API Client for RAG API

import {
  ChatResponse,
  DocumentIngestResponse,
  SearchResponse,
  Stats,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class RAGAPIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_URL) {
    this.baseUrl = baseUrl;
  }

  async uploadDocument(
    file: File,
    metadata?: Record<string, any>,
    userId: string = "default_user",
  ): Promise<DocumentIngestResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("metadata", JSON.stringify(metadata || {}));
    formData.append("user_id", userId);

    const response = await fetch(`${this.baseUrl}/documents/ingest`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Upload failed");
    }

    return response.json();
  }

  async chat(
    message: string,
    sessionId?: string,
    userId: string = "default_user",
    topK: number = 5,
    model: string = "gpt-4o-mini",
    includeSources: boolean = true,
  ): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        user_id: userId,
        top_k: topK,
        model,
        include_sources: includeSources,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Chat failed");
    }

    return response.json();
  }

  async chatStream(
    message: string,
    sessionId?: string,
    userId: string = "default_user",
    topK: number = 5,
    model: string = "gpt-4o-mini",
    onChunk: (chunk: string) => void = () => {},
    onMetadata?: (metadata: {
      session_id: string;
      sources: SourceChunk[];
    }) => void,
    onDone?: (stats: {
      tokens_used: number;
      cost_usd: number;
      processing_time_ms: number;
    }) => void,
    onError?: (error: string) => void,
  ): Promise<void> {
    const response = await fetch(`${this.baseUrl}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        user_id: userId,
        top_k: topK,
        model,
        include_sources: true,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error("No response body");
    }

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              switch (data.type) {
                case "metadata":
                  onMetadata?.(data);
                  break;
                case "content":
                  onChunk(data.delta);
                  break;
                case "done":
                  onDone?.(data);
                  break;
                case "error":
                  onError?.(data.message);
                  break;
              }
            } catch (e) {
              // Ignore JSON parse errors for incomplete chunks
              console.warn("Failed to parse SSE event:", e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async search(
    query: string,
    topK: number = 5,
    filter?: Record<string, any>,
  ): Promise<SearchResponse> {
    const response = await fetch(`${this.baseUrl}/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        top_k: topK,
        filter,
        include_text: true,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "Search failed");
    }

    return response.json();
  }

  async getStats(): Promise<Stats> {
    const response = await fetch(`${this.baseUrl}/stats`);

    if (!response.ok) {
      throw new Error("Failed to fetch stats");
    }

    return response.json();
  }

  async checkHealth(): Promise<any> {
    try {
      const stats = await this.getStats();
      return {
        api: true,
        vectorStore: stats.vector_count !== undefined,
        parsers: stats.parsers_registered > 0,
        embeddings: stats.embedding_model !== "unknown",
      };
    } catch (error) {
      return {
        api: false,
        vectorStore: false,
        parsers: false,
        embeddings: false,
      };
    }
  }

  async getHealth(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/health`);

    if (!response.ok) {
      throw new Error("Health check failed");
    }

    return response.json();
  }

  async listDocuments(userId: string = "default_user"): Promise<any> {
    const response = await fetch(`${this.baseUrl}/documents?user_id=${userId}`);

    if (!response.ok) {
      throw new Error("Failed to list documents");
    }

    return response.json();
  }

  async deleteDocument(documentId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/documents/${documentId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      throw new Error("Failed to delete document");
    }

    return response.json();
  }
}

// Singleton instance
export const apiClient = new RAGAPIClient();
