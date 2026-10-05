import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import { readFileSync } from "node:fs";
import { act, createElement as h } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Routes, Route, Link, useNavigate } from "react-router-dom";
import { JSDOM } from "jsdom";
import ConversationProvider from "../src/Chatbot/ConversationProvider.tsx";
import { useConversation } from "../src/Chatbot/ConversationContext.ts";

let dom, root, current, navigate, calls, resolveAnswer;
const originalFetch = globalThis.fetch;

function Probe() {
  current = useConversation();
  navigate = useNavigate();
  return h("div", null, current.messages.map((message) => h("p", { key: message.id }, message.content)),
    h(Link, { to: "/square-reports" }, "Square Reports"));
}

function tree() {
  return h(MemoryRouter, null, h(ConversationProvider, null,
    h(Routes, null,
      h(Route, { path: "/", element: h(Probe) }),
      h(Route, { path: "/square-reports", element: h("p", null, "Reports") }),
      h(Route, { path: "/vendor", element: h("p", null, "Vendors") }),
    )));
}

beforeEach(async () => {
  dom = new JSDOM('<div id="root"></div>', { url: "http://localhost/" });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  calls = [];
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("/api/locations")) return new Response(JSON.stringify([
      { id: 1, name: "A", is_active: true }, { id: 2, name: "B", is_active: true },
    ]));
    calls.push(JSON.parse(options.body));
    return new Promise((resolve) => {
      resolveAnswer = (answer = "**September overview**") => resolve(new Response(JSON.stringify({ answer, tool_calls_used: [] })));
    });
  };
  root = createRoot(document.getElementById("root"));
  await act(async () => root.render(tree()));
  await act(async () => current.changeLocation("1"));
});

afterEach(async () => {
  await act(async () => root.unmount());
  globalThis.fetch = originalFetch;
  dom.window.close();
  delete globalThis.window;
  delete globalThis.document;
  delete globalThis.IS_REACT_ACT_ENVIRONMENT;
});

async function send(question = "Overview") {
  let pending;
  await act(async () => { pending = current.submitQuestion(question); });
  await act(async () => { resolveAnswer(); await pending; });
}

test("shared provider preserves messages, location, and draft through route unmounts and back/forward", async () => {
  await send();
  await act(async () => current.setDraft("Unsent follow-up"));
  const messages = current.messages;
  await act(async () => document.querySelector("a").dispatchEvent(new window.MouseEvent("click", { bubbles: true, cancelable: true, button: 0 })));
  assert.equal(document.body.textContent, "Reports");
  await act(async () => navigate("/vendor"));
  assert.equal(document.body.textContent, "Vendors");
  await act(async () => navigate("/"));
  assert.deepEqual(current.messages, messages);
  assert.equal(current.draft, "Unsent follow-up");
  assert.equal(current.selectedLocationId, "1");
  await act(async () => navigate(-1));
  assert.equal(document.body.textContent, "Vendors");
  await act(async () => navigate(1));
  assert.deepEqual(current.messages, messages);
});

test("pending requests finish while away without duplication or losing the answer", async () => {
  let pending;
  await act(async () => {
    pending = current.submitQuestion("Overview");
    void current.submitQuestion("Duplicate");
  });
  await act(async () => navigate("/vendor"));
  await act(async () => { resolveAnswer(); await pending; });
  await act(async () => navigate("/"));
  assert.equal(calls.length, 1);
  assert.equal(current.messages.length, 2);
  assert.equal(current.isSubmitting, false);
});

test("new conversation clears shared history and draft while retaining location", async () => {
  await send();
  await act(async () => current.setDraft("Draft"));
  await act(async () => current.newConversation());
  assert.deepEqual(current.messages, []);
  assert.equal(current.draft, "");
  assert.equal(current.queryError, null);
  assert.equal(current.selectedLocationId, "1");
  await send("Fresh question");
  assert.deepEqual(calls.at(-1).history, []);
});

test("location change discards old messages, draft, and late answers", async () => {
  let pending;
  await act(async () => { pending = current.submitQuestion("Location A question"); });
  await act(async () => current.changeLocation("2"));
  await act(async () => { resolveAnswer("Old A answer"); await pending; });
  assert.deepEqual(current.messages, []);
  assert.equal(current.draft, "");
  await send("Location B question");
  assert.equal(calls.at(-1).location_id, 2);
  assert.deepEqual(calls.at(-1).history, []);
});

test("clearing during a request discards its late answer", async () => {
  let pending;
  await act(async () => { pending = current.submitQuestion("Old question"); });
  await act(async () => current.newConversation());
  await act(async () => { resolveAnswer(); await pending; });
  assert.deepEqual(current.messages, []);
  assert.equal(current.isSubmitting, false);
});

test("an old location response cannot replace or unlock a newer pending request", async () => {
  let oldPending, newPending;
  await act(async () => { oldPending = current.submitQuestion("A question"); });
  const finishOld = resolveAnswer;
  await act(async () => current.changeLocation("2"));
  await act(async () => { newPending = current.submitQuestion("B question"); });
  const finishNew = resolveAnswer;
  await act(async () => { finishOld("A answer"); await oldPending; });
  assert.equal(current.isSubmitting, true);
  assert.deepEqual(current.messages.map(({ content }) => content), ["B question"]);
  await act(async () => { finishNew("B answer"); await newPending; });
  assert.deepEqual(current.messages.map(({ content }) => content), ["B question", "B answer"]);
});

test("request errors remain UI state and recover on the next question", async () => {
  const fakeFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response("failure", { status: 503 });
  await act(async () => current.submitQuestion("Failed question"));
  assert.equal(current.isSubmitting, false);
  assert.ok(current.queryError);
  assert.deepEqual(current.messages.map(({ role }) => role), ["user"]);
  globalThis.fetch = fakeFetch;
  await send("Try again");
  assert.equal(current.queryError, null);
  assert.deepEqual(calls.at(-1).history, [{ role: "user", content: "Failed question" }]);
});

test("fresh app mount resets conversation without browser storage", async () => {
  await send();
  await act(async () => current.setDraft("Draft"));
  await act(async () => root.unmount());
  root = createRoot(document.getElementById("root"));
  await act(async () => root.render(tree()));
  assert.deepEqual(current.messages, []);
  assert.equal(current.draft, "");
  assert.equal(current.selectedLocationId, "");
  assert.equal(window.localStorage.length, 0);
  assert.equal(window.sessionStorage.length, 0);
});

test("API history excludes current question and UI errors/loading", async () => {
  await send("First");
  await act(async () => current.setQueryError("UI failure"));
  await send("Follow-up");
  assert.deepEqual(calls.at(-1).history, [
    { role: "user", content: "First" },
    { role: "assistant", content: "**September overview**" },
  ]);
  assert.equal(calls.at(-1).question, "Follow-up");
});

test("app mounts provider above routes and navbar uses SPA links", () => {
  const main = readFileSync(new URL("../src/main.tsx", import.meta.url), "utf8");
  const navbar = readFileSync(new URL("../src/Navbar/Navbar.tsx", import.meta.url), "utf8");
  assert.match(main, /<ConversationProvider>[\s\S]*<Routes>[\s\S]*<\/Routes>[\s\S]*<\/ConversationProvider>/);
  assert.doesNotMatch(navbar, /<a\s/);
  assert.match(navbar, /<Link[^>]*to=/);
});
