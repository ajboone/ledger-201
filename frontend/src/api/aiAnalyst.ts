import { apiRequest } from "./client";
import type {
  AIAnalystQueryRequest,
  AIAnalystQueryResponse,
} from "../types/aiAnalyst";

export function queryAIAnalyst(
  question: string,
  locationId: number,
): Promise<AIAnalystQueryResponse> {
  const request: AIAnalystQueryRequest = {
    question,
    location_id: locationId,
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
