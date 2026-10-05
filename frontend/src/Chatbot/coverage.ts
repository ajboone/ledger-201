export interface DataCoverage {
  location_id: number;
  latest_monthly_report_start: string | null;
  latest_monthly_report_end: string | null;
  has_monthly_reports: boolean;
  has_real_transaction_data: boolean;
  available_real_granularity: string[];
}

export function coverageLines(coverage: DataCoverage): string[] {
  const formatDate = (value: string) => new Intl.DateTimeFormat("en-US", {
    month: "short", day: "numeric", year: "numeric", timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
  const start = coverage.latest_monthly_report_start;
  const end = coverage.latest_monthly_report_end;
  return [
    coverage.has_monthly_reports && start && end
      ? `Latest real report: ${formatDate(start)} – ${formatDate(end)}`
      : "No real monthly reports imported for this location.",
    ...(coverage.has_monthly_reports ? ["Source: Square Sales Report"] : []),
    `Real data granularity: ${coverage.available_real_granularity.map((value) => ({
      monthly_aggregate: "Monthly aggregate", daily: "Daily", transaction: "Transaction",
    })[value] ?? value).join(", ") || "Not available"}`,
    `Day-level real transaction data: ${coverage.has_real_transaction_data ? "Available (recorded dates only)" : "Not available"}`,
  ];
}
