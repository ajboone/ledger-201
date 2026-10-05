import {
  MAX_AI_ANALYST_HISTORY_CONTENT_LENGTH,
  MAX_AI_ANALYST_HISTORY_MESSAGES,
} from "../types/aiAnalyst.ts";
import type { AIAnalystConversationMessage } from "../types/aiAnalyst.ts";

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
}

export type ConversationAction =
  | { type: "append"; message: ChatMessage }
  | { type: "clear" };

interface HistoryCandidate {
  role: string;
  content: string;
}

export function conversationReducer(
  messages: ChatMessage[],
  action: ConversationAction,
): ChatMessage[] {
  if (action.type === "clear") {
    return [];
  }
  return [...messages, action.message];
}

export function buildConversationHistory(
  messages: readonly HistoryCandidate[],
): AIAnalystConversationMessage[] {
  return messages
    .filter(
      (message): message is AIAnalystConversationMessage =>
        message.role === "user" || message.role === "assistant",
    )
    .slice(-MAX_AI_ANALYST_HISTORY_MESSAGES)
    .map(({ role, content }) => ({
      role,
      content: content.slice(-MAX_AI_ANALYST_HISTORY_CONTENT_LENGTH),
    }));
}
