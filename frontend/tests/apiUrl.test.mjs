import assert from "node:assert/strict";
import test from "node:test";
import { apiUrl } from "../src/api/url.ts";

test("development retains the local backend default", () => {
  assert.equal(apiUrl("/api/vendors", undefined, false), "http://127.0.0.1:8000/api/vendors");
});

test("production uses same-origin API paths without duplicating api", () => {
  for (const path of ["/api/vendors", "/api/square-reports?location_id=1", "/api/ai-analyst/query", "/api"]) {
    assert.equal(apiUrl(path, undefined, true), path);
  }
});

test("explicit origins and API bases work in either mode", () => {
  for (const production of [true, false]) {
    for (const base of ["https://ledger.example.com", "https://ledger.example.com/", "https://ledger.example.com/api", "https://ledger.example.com/api/"]) {
      assert.equal(apiUrl("/api/locations", base, production), "https://ledger.example.com/api/locations");
    }
    assert.equal(apiUrl("/api/vendors", "", production), "/api/vendors");
    assert.equal(apiUrl("/api/vendors", "/api", production), "/api/vendors");
  }
});
