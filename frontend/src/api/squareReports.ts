import { apiRequest } from "./client";
import type {
  SquareSalesReportDetail,
  SquareSalesReportImportRequest,
  SquareSalesReportImportResult,
  SquareSalesReportSummary,
} from "../types/squareReport";

export function importSquareSalesReport(
  locationId: number,
  rawReportText: string,
): Promise<SquareSalesReportImportResult> {
  const request: SquareSalesReportImportRequest = {
    location_id: locationId,
    raw_report_text: rawReportText,
  };

  return apiRequest<SquareSalesReportImportResult>(
    "/api/square-reports/import",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
    "Square Sales Report",
  );
}

export function getSquareSalesReports(
  locationId?: number,
): Promise<SquareSalesReportSummary[]> {
  const query = locationId
    ? `?${new URLSearchParams({ location_id: String(locationId) }).toString()}`
    : "";
  return apiRequest<SquareSalesReportSummary[]>(
    `/api/square-reports${query}`,
    {},
    "Square Sales Report history",
  );
}

export function getSquareSalesReport(
  reportId: number,
): Promise<SquareSalesReportDetail> {
  return apiRequest<SquareSalesReportDetail>(
    `/api/square-reports/${reportId}`,
    {},
    "Square Sales Report details",
  );
}
