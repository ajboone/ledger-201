import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import { getLocations } from "../api/locations";
import { queryAIAnalyst } from "../api/aiAnalyst";
import pulseAnimation from "../assets/pulse-green.lottie";
import type { Location } from "../types/location";
import { typography } from "../typography";
import TextInput from "./TextInput";
import { ledgerSpanStyles } from "./styles";
import "./Chatbot.css";

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
}

const starterPrompts = [
  "Summarize September 14, 2026.",
  "Which orders need attention on September 14, 2026?",
  "What were the top items on September 13, 2026?",
  "Compare September 12 and September 16, 2026.",
];

function queryErrorMessage(error: unknown): string {
  if (!(error instanceof Error)) {
    return "Ledger couldn't complete that request. Please try again.";
  }

  const message = error.message.toLowerCase();
  if (message.includes("not configured") || message.includes("unavailable")) {
    return "The analyst service isn't available right now. Please try again later.";
  }
  if (
    message.includes("failed to fetch") ||
    message.includes("networkerror") ||
    message.includes("request failed")
  ) {
    return "Ledger couldn't reach the analyst service. Check your connection and try again.";
  }
  return "Ledger couldn't complete that analysis just now. Please try again.";
}

export const Chatbot = () => {
  const [locations, setLocations] = useState<Location[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isLoadingLocations, setIsLoadingLocations] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const nextMessageId = useRef(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;

    async function loadLocations() {
      try {
        const availableLocations = await getLocations();
        if (!active) return;

        const activeLocations = availableLocations.filter(
          (location) => location.is_active,
        );
        setLocations(activeLocations);
        if (activeLocations.length === 1) {
          setSelectedLocationId(String(activeLocations[0].id));
        }
      } catch {
        if (active) {
          setLocationError(
            "Couldn't load your Ledger locations. Please refresh and try again.",
          );
        }
      } finally {
        if (active) setIsLoadingLocations(false);
      }
    }

    void loadLocations();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSubmitting]);

  async function submitQuestion(question: string) {
    const normalizedQuestion = question.trim();
    if (!normalizedQuestion || !selectedLocationId || isSubmitting) return;

    setQueryError(null);
    setDraft("");
    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: nextMessageId.current++,
        role: "user",
        content: normalizedQuestion,
      },
    ]);
    setIsSubmitting(true);

    try {
      const response = await queryAIAnalyst(
        normalizedQuestion,
        Number(selectedLocationId),
      );
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: nextMessageId.current++,
          role: "assistant",
          content: response.answer,
        },
      ]);
    } catch (error) {
      setQueryError(queryErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.trim()) {
      setQueryError("Type a question first and Ledger will take a look.");
      return;
    }
    if (!selectedLocationId) {
      setQueryError("Choose a Ledger location before asking a question.");
      return;
    }
    void submitQuestion(draft);
  }

  function handleLocationChange(locationId: string) {
    setSelectedLocationId(locationId);
    setMessages([]);
    setQueryError(null);
  }

  return (
    <div className="chatbot-container">
      {messages.length === 0 && (
        <div className="chatbot-heading">
          <DotLottieReact
            src={pulseAnimation}
            autoplay
            loop
            style={{
              width: "150px",
              height: "150px",
              pointerEvents: "none",
              margin: "0 auto",
            }}
          />
          <h2 style={typography.h2}>
            Hey, I&apos;m <span style={ledgerSpanStyles}>ledger</span>. How can I
            help you today?
          </h2>
        </div>
      )}

      <label className="chatbot-location" htmlFor="chatbot-location">
        Location
        <select
          id="chatbot-location"
          value={selectedLocationId}
          onChange={(event) => handleLocationChange(event.target.value)}
          disabled={isLoadingLocations || locations.length === 0 || isSubmitting}
        >
          <option value="">
            {isLoadingLocations
              ? "Loading locations..."
              : locations.length === 0
                ? "No active locations"
                : "Choose a location"}
          </option>
          {locations.map((location) => (
            <option key={location.id} value={location.id}>
              {location.name}
            </option>
          ))}
        </select>
      </label>

      {isLoadingLocations && (
        <p className="chatbot-status" role="status">
          Loading your Ledger locations...
        </p>
      )}
      {locationError && (
        <p className="chatbot-status chatbot-error" role="alert">
          {locationError}
        </p>
      )}
      {!isLoadingLocations && locations.length === 0 && !locationError && (
        <p className="chatbot-status">
          Add an active location to start chatting with Ledger.
        </p>
      )}

      {messages.length > 0 && (
        <section className="chatbot-messages" aria-label="Conversation" aria-live="polite">
          {messages.map((message) => (
            <article
              className={`chatbot-message chatbot-message-${message.role}`}
              key={message.id}
            >
              <p className="chatbot-message-label">
                {message.role === "user" ? "You" : "Ledger"}
              </p>
              <p>{message.content}</p>
            </article>
          ))}
          {isSubmitting && (
            <p className="chatbot-status" role="status">
              Ledger is checking the numbers...
            </p>
          )}
          <div ref={messagesEndRef} />
        </section>
      )}

      {messages.length === 0 && locations.length > 0 && (
        <div className="chatbot-starters" aria-label="Starter questions">
          {starterPrompts.map((prompt) => (
            <button
              className="chatbot-starter"
              disabled={!selectedLocationId || isSubmitting}
              key={prompt}
              onClick={() => void submitQuestion(prompt)}
              type="button"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {queryError && (
        <p className="chatbot-status chatbot-error" role="alert">
          {queryError}
        </p>
      )}
      <TextInput
        disabled={!selectedLocationId || isLoadingLocations || isSubmitting}
        isSubmitting={isSubmitting}
        onChange={setDraft}
        onSubmit={handleSubmit}
        value={draft}
      />
    </div>
  );
};

export default Chatbot;
