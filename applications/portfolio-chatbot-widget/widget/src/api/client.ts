/**
 * API Client for Portfolio Chatbot Widget
 */

import type { ChatResponse, LeadData } from "../types";

export class ChatbotAPIClient {
  private apiUrl: string;
  private userId: string;

  constructor(apiUrl: string, userId: string = "widget_user") {
    this.apiUrl = apiUrl.replace(/\/$/, ""); // Remove trailing slash
    this.userId = userId;
  }

  async sendMessage(
    message: string,
    sessionId?: string,
  ): Promise<ChatResponse> {
    const response = await fetch(`${this.apiUrl}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        user_id: this.userId,
        top_k: 5,
        model: "gpt-4o-mini",
        include_sources: true,
      }),
    });

    if (!response.ok) {
      throw new Error(`Chat API error: ${response.statusText}`);
    }

    return response.json();
  }

  async captureLead(
    sessionId: string,
    leadData: LeadData,
    interestLevel: string = "medium",
  ): Promise<{ lead_id: string; message: string }> {
    const response = await fetch(`${this.apiUrl}/leads/capture`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: sessionId,
        ...leadData,
        interest_level: interestLevel,
      }),
    });

    if (!response.ok) {
      throw new Error(`Lead capture API error: ${response.statusText}`);
    }

    return response.json();
  }
}
