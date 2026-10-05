import { useEffect, useReducer, useRef, useState } from "react";
import type { ReactNode } from "react";
import { getLocations } from "../api/locations";
import { queryAIAnalyst } from "../api/aiAnalyst";
import type { Location } from "../types/location";
import { buildConversationHistory, conversationReducer } from "./conversation";
import { ConversationContext } from "./ConversationContext";

function queryErrorMessage(error: unknown): string {
  if (!(error instanceof Error)) {
    return "Ledger couldn't complete that request. Please try again.";
  }
  const message = error.message.toLowerCase();
  if (message.includes("not configured") || message.includes("unavailable")) {
    return "The analyst service isn't available right now. Please try again later.";
  }
  if (message.includes("failed to fetch") || message.includes("networkerror") || message.includes("request failed")) {
    return "Ledger couldn't reach the analyst service. Check your connection and try again.";
  }
  return "Ledger couldn't complete that analysis just now. Please try again.";
}

// Memory only: this owner outlives routes, but a full page reload starts fresh.
export default function ConversationProvider({ children }: { children: ReactNode }) {
  const [messages, dispatchMessage] = useReducer(conversationReducer, []);
  const [locations, setLocations] = useState<Location[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState("");
  const [draft, setDraft] = useState("");
  const [isLoadingLocations, setIsLoadingLocations] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const nextMessageId = useRef(0);
  const activeRequest = useRef<object | null>(null);

  useEffect(() => {
    let active = true;
    getLocations().then((available) => {
      if (!active) return;
      const activeLocations = available.filter((location) => location.is_active);
      setLocations(activeLocations);
      if (activeLocations.length === 1) setSelectedLocationId(String(activeLocations[0].id));
    }).catch(() => {
      if (active) setLocationError("Couldn't load your Ledger locations. Please refresh and try again.");
    }).finally(() => {
      if (active) setIsLoadingLocations(false);
    });
    return () => {
      active = false;
      activeRequest.current = null;
    };
  }, []);

  function newConversation() {
    // A late response from a cleared conversation must never enter a new one.
    activeRequest.current = null;
    dispatchMessage({ type: "clear" });
    setDraft("");
    setQueryError(null);
    setIsSubmitting(false);
  }

  function changeLocation(locationId: string) {
    if (locationId === selectedLocationId) return;
    newConversation();
    setSelectedLocationId(locationId);
  }

  async function submitQuestion(question: string) {
    const normalizedQuestion = question.trim();
    if (!normalizedQuestion || !selectedLocationId || activeRequest.current) return;
    const request = {};
    activeRequest.current = request;
    const history = buildConversationHistory(messages);
    setQueryError(null);
    setDraft("");
    dispatchMessage({ type: "append", message: {
      id: nextMessageId.current++, role: "user", content: normalizedQuestion,
    } });
    setIsSubmitting(true);
    try {
      const response = await queryAIAnalyst(normalizedQuestion, Number(selectedLocationId), history);
      if (activeRequest.current !== request) return;
      dispatchMessage({ type: "append", message: {
        id: nextMessageId.current++, role: "assistant", content: response.answer,
      } });
    } catch (error) {
      if (activeRequest.current === request) setQueryError(queryErrorMessage(error));
    } finally {
      if (activeRequest.current === request) {
        activeRequest.current = null;
        setIsSubmitting(false);
      }
    }
  }

  return <ConversationContext.Provider value={{
    messages, locations, selectedLocationId, draft, isLoadingLocations, isSubmitting,
    locationError, queryError, setDraft, setQueryError, changeLocation,
    newConversation, submitQuestion,
  }}>{children}</ConversationContext.Provider>;
}
