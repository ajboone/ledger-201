export const MAX_AI_ANALYST_HISTORY_MESSAGES = 10;
export const MAX_AI_ANALYST_HISTORY_CONTENT_LENGTH = 2000;

export interface AIAnalystConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AIAnalystQueryRequest {
  question: string;
  location_id: number;
  history: AIAnalystConversationMessage[];
}

export interface AIAnalystToolCallTrace {
  tool: string;
  arguments: Record<string, unknown>;
}

export interface AIAnalystQueryResponse {
  answer: string;
  tool_calls_used: AIAnalystToolCallTrace[];
}
