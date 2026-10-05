import { useEffect, useRef } from "react";
import type { FormEvent } from "react";
import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import pulseAnimation from "../assets/pulse-green.lottie";
import { typography } from "../typography";
import { useConversation } from "./ConversationContext";
import TextInput from "./TextInput";
import { ledgerSpanStyles } from "./styles";
import "./Chatbot.css";
import DataCoverage from "./DataCoverage";
import MessageContent from "./MessageContent";

const starterPrompts = [
  "Summarize the latest imported month.",
  "What were the top items in the latest report?",
  "How much was discounted in the latest report?",
  "What real data is available?",
];

export const Chatbot = () => {
  const {
    locations, selectedLocationId, messages, draft, isLoadingLocations,
    isSubmitting, locationError, queryError, setDraft, setQueryError,
    changeLocation, newConversation, submitQuestion,
  } = useConversation();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSubmitting]);
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
          onChange={(event) => changeLocation(event.target.value)}
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
      <DataCoverage key={selectedLocationId} locationId={selectedLocationId} />

      {messages.length > 0 && (
        <div className="chatbot-actions">
          <span>Chat stays while you browse. Reloading clears it.</span>
          <button
            className="chatbot-new-conversation"
            disabled={isSubmitting}
            onClick={newConversation}
            type="button"
          >
            New conversation
          </button>
        </div>
      )}

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
              <MessageContent role={message.role} content={message.content} />
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
