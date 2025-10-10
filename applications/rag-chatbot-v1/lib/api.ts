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
  ): Promise<DocumentIngestResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("metadata", JSON.stringify(metadata || {}));

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
    userId: string = "web_user",
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

  async getHealth(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/health`);

    if (!response.ok) {
      throw new Error("Health check failed");
    }

    return response.json();
  }
}

// Singleton instance
export const apiClient = new RAGAPIClient();
