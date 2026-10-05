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

const salesTable = "| Item | Reported sales | Units |\n|---|---:|---:|\n| **Teriyaki Chicken** | $2,386.40 | 158 |\n| Hibachi Steak | $1,806.14 | 86 |";

test("assistant GFM tables render semantic headers, rows, aligned numbers, and inline emphasis", () => {
  const body = render(salesTable);
  assert.equal(body.querySelectorAll("table").length, 1);
  assert.deepEqual([...body.querySelectorAll("thead th")].map((cell) => cell.textContent), ["Item", "Reported sales", "Units"]);
  assert.equal(body.querySelectorAll("tbody tr").length, 2);
  assert.equal(body.querySelectorAll("tbody td").length, 6);
  assert.equal(body.querySelector("td strong").textContent, "Teriyaki Chicken");
  assert.equal(body.querySelector("tbody td:nth-child(2)").textContent, "$2,386.40");
  assert.equal(body.querySelector("tbody td:nth-child(2)").style.textAlign, "right");
  assert.doesNotMatch(body.textContent, /\|---|\*\*/);
});

test("tables have a labeled, keyboard-focusable scroll wrapper", () => {
  const body = render(salesTable);
  const wrapper = body.querySelector("table").parentElement;
  assert.equal(wrapper.className, "chatbot-table-scroll");
  assert.equal(wrapper.getAttribute("role"), "region");
  assert.equal(wrapper.getAttribute("aria-label"), "Assistant data table");
  assert.equal(wrapper.tabIndex, 0);
});

test("user table syntax stays plain text", () => {
  const body = render(salesTable, "user");
  assert.equal(body.textContent, salesTable);
  assert.equal(body.querySelector("table, strong"), null);
});

test("raw HTML stays disabled inside GFM tables", () => {
  const body = render('| Item | Sales |\n|---|---:|\n| <img src=x onerror="alert(1)">Safe | $10 |');
  assert.equal(body.querySelectorAll("table").length, 1);
  assert.equal(body.querySelector("img, script"), null);
  assert.doesNotMatch(body.innerHTML, /onerror=/);
});
