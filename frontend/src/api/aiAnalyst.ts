import { apiRequest } from "./client";
import type {
  AIAnalystConversationMessage,
  AIAnalystQueryRequest,
  AIAnalystQueryResponse,
} from "../types/aiAnalyst";

export function queryAIAnalyst(
  question: string,
  locationId: number,
  history: AIAnalystConversationMessage[],
): Promise<AIAnalystQueryResponse> {
  const request: AIAnalystQueryRequest = {
    question,
    location_id: locationId,
    history,
  };

  return apiRequest<AIAnalystQueryResponse>(
    "/api/ai-analyst/query",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
    "AI Analyst",
  );
}
