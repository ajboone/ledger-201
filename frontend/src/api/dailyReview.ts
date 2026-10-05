import { apiRequest } from "./client";
import type { DailyReview } from "../types/dailyReview";

export function getDailyReview(
  locationId: number,
  reviewDate: string,
): Promise<DailyReview> {
  const query = new URLSearchParams({
    location_id: String(locationId),
    date: reviewDate,
    provenance: "demo",
  });
  return apiRequest<DailyReview>(
    `/api/daily-review?${query.toString()}`,
    {},
    "Daily review",
  );
}
