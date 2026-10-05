import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import { coverageLines } from "./coverage";
import type { DataCoverage as Coverage } from "./coverage";

export default function DataCoverage({ locationId }: { locationId: string }) {
  const [result, setResult] = useState<{ locationId: string; data?: Coverage; error?: boolean } | null>(null);
  useEffect(() => {
    if (!locationId) return;
    let active = true;
    apiRequest<Coverage>(`/api/analyst/coverage?location_id=${encodeURIComponent(locationId)}`, {}, "Data coverage")
      .then((data) => { if (active) setResult({ locationId, data }); })
      .catch(() => { if (active) setResult({ locationId, error: true }); });
    return () => { active = false; };
  }, [locationId]);
  const current = result?.locationId === locationId ? result : null;
  return (
    <aside className="chatbot-coverage" aria-label="What Ledger knows" aria-live="polite">
      <strong>What Ledger knows</strong>
      {!locationId ? <p>Choose a location to see its real data coverage.</p>
        : current?.data ? coverageLines(current.data).map((line) => <p key={line}>{line}</p>)
        : <p>{current?.error ? "Couldn't load data coverage. Try reselecting this location." : "Loading data coverage..."}</p>}
    </aside>
  );
}
