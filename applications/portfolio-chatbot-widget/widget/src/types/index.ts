/**
 * Type definitions for Portfolio Chatbot Widget
 */

export interface WidgetConfig {
  apiUrl: string;
  cdnUrl?: string;
  userId?: string;
  primaryColor?: string;
  position?: "bottom-right" | "bottom-left" | "top-right" | "top-left";
  greeting?: string;
  leadCapture?: LeadCaptureConfig;
  tools?: string[];
}

export interface LeadCaptureConfig {
  enabled: boolean;
  timing: "immediate" | "on_signal" | "on_exit";
  fields: Array<"name" | "email" | "company" | "role">;
}

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceChunk[];
  tool_calls?: ToolCall[];
  timestamp: Date;
}

export interface SourceChunk {
  chunk_id: string;
  score: number;
  text?: string;
}

export interface ToolCall {
  tool: string;
  action: "link" | "form";
  url?: string;
  text: string;
  data?: any;
}

export interface ChatResponse {
  answer: string;
  session_id: string;
  sources: SourceChunk[];
  model: string;
  tokens_used: number;
  cost_usd: number;
  processing_time_ms: number;
  tool_calls: ToolCall[];
  lead_capture?: LeadCapturePrompt;
}

export interface LeadCapturePrompt {
  should_capture: boolean;
  interest_level: "low" | "medium" | "high";
  trigger: string;
  message?: string;
}

export interface LeadData {
  email?: string;
  name?: string;
  company?: string;
  role?: string;
}

export interface ChatState {
  isOpen: boolean;
  isMinimized: boolean;
  messages: Message[];
  isLoading: boolean;
  sessionId?: string;
  showLeadForm: boolean;
  leadCaptureMessage?: string;
}
