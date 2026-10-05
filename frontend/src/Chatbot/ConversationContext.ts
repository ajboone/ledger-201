import { createContext, useContext } from "react";
import type { ChatMessage } from "./conversation";
import type { Location } from "../types/location";

interface ConversationContextValue {
  messages: ChatMessage[];
  locations: Location[];
  selectedLocationId: string;
  draft: string;
  isLoadingLocations: boolean;
  isSubmitting: boolean;
  locationError: string | null;
  queryError: string | null;
  setDraft: (draft: string) => void;
  setQueryError: (error: string | null) => void;
  changeLocation: (locationId: string) => void;
  newConversation: () => void;
  submitQuestion: (question: string) => Promise<void>;
}

export const ConversationContext = createContext<ConversationContextValue | null>(null);

export function useConversation() {
  const context = useContext(ConversationContext);
  if (!context) throw new Error("Chatbot requires ConversationProvider.");
  return context;
}
