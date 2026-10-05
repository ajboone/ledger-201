import assert from "node:assert/strict";
import test from "node:test";

import {
  buildConversationHistory,
  conversationReducer,
} from "../src/Chatbot/conversation.ts";

test("history contains only the ten newest user and assistant messages", () => {
  const messages = Array.from({ length: 12 }, (_, index) => ({
    id: index,
    role: index % 2 === 0 ? "user" : "assistant",
    content: `Message ${index}`,
  }));

  assert.deepEqual(
    buildConversationHistory(messages).map(({ content }) => content),
    [
      "Message 2",
      "Message 3",
      "Message 4",
      "Message 5",
      "Message 6",
      "Message 7",
      "Message 8",
      "Message 9",
      "Message 10",
      "Message 11",
    ],
  );
});

test("history trims oversized content and excludes UI error/status entries", () => {
  const history = buildConversationHistory([
    { role: "user", content: "Prior question" },
    { role: "error", content: "UI error: request failed" },
    { role: "loading", content: "Ledger is checking..." },
    { role: "assistant", content: "x".repeat(2001) },
  ]);

  assert.deepEqual(history.map(({ role }) => role), ["user", "assistant"]);
  assert.equal(history[1].content.length, 2000);
  assert.equal(history[1].content, "x".repeat(2000));
});

test("current question is appended after history is captured, not duplicated", () => {
  const previousMessages = [
    { id: 1, role: "user", content: "September 2026" },
    { id: 2, role: "assistant", content: "The report covers September." },
  ];
  const history = buildConversationHistory(previousMessages);
  const withCurrentQuestion = conversationReducer(previousMessages, {
    type: "append",
    message: { id: 3, role: "user", content: "What about refunds?" },
  });

  assert.equal(history.some(({ content }) => content === "What about refunds?"), false);
  assert.equal(withCurrentQuestion.at(-1)?.content, "What about refunds?");
});

test("clearing the conversation removes visible messages and future context", () => {
  const messages = [
    { id: 1, role: "user", content: "September 2026" },
    { id: 2, role: "assistant", content: "September's report..." },
  ];

  const clearedMessages = conversationReducer(messages, { type: "clear" });

  assert.deepEqual(clearedMessages, []);
  assert.deepEqual(buildConversationHistory(clearedMessages), []);
});
