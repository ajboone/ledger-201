export interface AIAnalystQueryRequest {
  question: string;
  location_id: number;
}

export interface AIAnalystToolCallTrace {
  tool: string;
  arguments: Record<string, unknown>;
}

export interface AIAnalystQueryResponse {
  answer: string;
  tool_calls_used: AIAnalystToolCallTrace[];
}
