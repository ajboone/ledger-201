import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { JSDOM } from "jsdom";
import MessageContent from "../src/Chatbot/MessageContent.tsx";

function render(content, role = "assistant") {
  return new JSDOM(renderToStaticMarkup(createElement(MessageContent, { role, content }))).window.document.body;
}

test("assistant bold and heading syntax becomes emphasized text and section labels", () => {
  const body = render("**The biggest takeaway**\n\n### Sales and money collected\n\n**Net sales:** $53,218.32");
  assert.equal(body.querySelector("strong").textContent, "The biggest takeaway");
  assert.equal(body.querySelector(".chatbot-section-label").textContent, "Sales and money collected");
  assert.doesNotMatch(body.textContent, /\*\*|###/);
  assert.match(body.textContent, /\$53,218\.32/);
});

test("assistant lists, emphasis, inline code, and links are semantic and keyboard accessible", () => {
  const body = render("- **Net sales:** $100\n- *Refunds:* $5\n\n1. Review `net sales`\n2. Open [Square](https://squareup.com)");
  assert.equal(body.querySelectorAll("ul > li").length, 2);
  assert.equal(body.querySelectorAll("ol > li").length, 2);
  assert.equal(body.querySelector("em").textContent, "Refunds:");
  assert.equal(body.querySelector("code").textContent, "net sales");
  assert.equal(body.querySelector("a").getAttribute("href"), "https://squareup.com");
  assert.match(body.querySelector("a").rel, /noopener/);
});

test("user messages preserve literal Markdown and escape HTML", () => {
  const text = "### My question\n**hello** <script>alert(1)</script>";
  const body = render(text, "user");
  assert.equal(body.textContent, text);
  assert.equal(body.querySelector("strong, script, h3"), null);
});

test("assistant HTML and unsafe URLs cannot become executable content", () => {
  const body = render('<script>alert(1)</script>\n\n<img src=x onerror="alert(1)">\n\n[unsafe](javascript:alert%281%29)');
  assert.equal(body.querySelector("script, img, iframe"), null);
  assert.doesNotMatch(body.innerHTML, /javascript:|onerror=/);
});
