import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { coverageLines } from "../src/Chatbot/coverage.ts";

const monthly = {
  location_id: 1,
  has_monthly_reports: true,
  latest_monthly_report_start: "2026-09-01",
  latest_monthly_report_end: "2026-09-30",
  has_real_transaction_data: false,
  available_real_granularity: ["monthly_aggregate"],
};
const source = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

test("coverage helper displays latest real monthly period and source", () => {
  assert.deepEqual(coverageLines(monthly), [
    "Latest real report: Sep 1, 2026 – Sep 30, 2026",
    "Source: Square Sales Report",
    "Real data granularity: Monthly aggregate",
    "Day-level real transaction data: Not available",
  ]);
});

test("coverage dates come from the backend, without September assumptions", () => {
  assert.match(coverageLines({ ...monthly, latest_monthly_report_start: "2027-02-01", latest_monthly_report_end: "2027-02-28" })[0], /Feb 1, 2027 – Feb 28, 2027/);
});

test("empty coverage does not imply monthly or daily availability", () => {
  assert.deepEqual(coverageLines({ ...monthly, has_monthly_reports: false, latest_monthly_report_start: null, latest_monthly_report_end: null, available_real_granularity: [] }), [
    "No real monthly reports imported for this location.",
    "Real data granularity: Not available",
    "Day-level real transaction data: Not available",
  ]);
});

test("explicit real transactions show bounded daily availability", () => {
  assert.match(coverageLines({ ...monthly, has_real_transaction_data: true }).at(-1), /Available \(recorded dates only\)/);
});

test("Daily Review navigation and page explicitly label synthetic demo data", () => {
  assert.match(source("../src/Navbar/Navbar.tsx"), /Daily Review \(Demo\)/);
  assert.match(source("../src/DailyReview/DailyReview.tsx"), /<h1>Daily Review \(Demo\)<\/h1>/);
  assert.match(source("../src/DailyReview/DailyReview.tsx"), /synthetic transaction data/);
  assert.match(source("../src/api/dailyReview.ts"), /provenance: "demo"/);
});

test("Square Reports preserves provenance and monthly limitation", () => {
  const page = source("../src/SquareReports/SquareReports.tsx");
  assert.match(page, /<dt>Source<\/dt>\s*<dd>Square Sales Report<\/dd>/);
  assert.match(page, /does not contain day-level transaction detail/);
  assert.match(page, /formatDateTime\(report.created_at\)/);
});
