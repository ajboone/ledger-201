import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  getSquareSalesReport,
  getSquareSalesReports,
  importSquareSalesReport,
} from "../api/squareReports";
import { getLocations } from "../api/locations";
import type { Location } from "../types/location";
import type {
  SquareSalesReportDetail,
  SquareSalesReportImportResult,
  SquareSalesReportSummary,
} from "../types/squareReport";
import { formatMoney } from "../utils/formatMoney";
import "./SquareReports.css";

function formatDate(value: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatDateTime(value: string | null): string {
  if (!value) return "Not included";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
}

function formatQuantity(quantity: number): string {
  return new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 4,
  }).format(quantity);
}

function getImportErrorMessage(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  const normalized = message.toLowerCase();

  if (normalized.includes("already exists") || normalized.includes("409")) {
    return "This report period has already been imported for this location.";
  }
  if (normalized.includes("location not found") || normalized.includes("404")) {
    return "That location is no longer available. Choose an active location and try again.";
  }
  if (normalized.includes("date range")) {
    return "We couldn't find the report date range. Paste the complete Square Sales Report text.";
  }
  if (normalized.includes("missing required report metrics")) {
    return "The report is missing required sales or payment totals. Paste the complete Square Sales Report.";
  }
  if (normalized.includes("currency") || normalized.includes("malformed")) {
    return "Some report values couldn't be read. Check the pasted text and try again.";
  }
  return "The report couldn't be imported. Check the pasted text and your connection, then try again.";
}

function sortReports(
  reports: SquareSalesReportSummary[],
): SquareSalesReportSummary[] {
  return [...reports].sort(
    (first, second) =>
      second.report_start.localeCompare(first.report_start) ||
      second.id - first.id,
  );
}

const SquareReports = () => {
  const [locations, setLocations] = useState<Location[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState("");
  const [reports, setReports] = useState<SquareSalesReportSummary[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [reportDetail, setReportDetail] = useState<SquareSalesReportDetail | null>(
    null,
  );
  const [rawReportText, setRawReportText] = useState("");
  const [importResult, setImportResult] =
    useState<SquareSalesReportImportResult | null>(null);

  const [isLoadingLocations, setIsLoadingLocations] = useState(true);
  const [isLoadingReports, setIsLoadingReports] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [locationsError, setLocationsError] = useState(false);
  const [reportsError, setReportsError] = useState(false);
  const [detailError, setDetailError] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const selectedLocation = useMemo(
    () => locations.find((location) => String(location.id) === selectedLocationId),
    [locations, selectedLocationId],
  );

  useEffect(() => {
    let active = true;

    async function loadLocations() {
      try {
        const locationData = await getLocations();
        if (!active) return;
        const activeLocations = locationData.filter((location) => location.is_active);
        setLocations(activeLocations);
        if (activeLocations.length === 1) {
          setIsLoadingReports(true);
          setSelectedLocationId(String(activeLocations[0].id));
        }
      } catch {
        if (active) setLocationsError(true);
      } finally {
        if (active) setIsLoadingLocations(false);
      }
    }

    void loadLocations();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedLocationId) {
      return;
    }

    let active = true;

    async function loadReports() {
      try {
        const reportData = sortReports(
          await getSquareSalesReports(Number(selectedLocationId)),
        );
        if (!active) return;
        setReports(reportData);
        const newestReport = reportData[0];
        if (newestReport) {
          setIsLoadingDetail(true);
          setSelectedReportId(newestReport.id);
        }
      } catch {
        if (active) setReportsError(true);
      } finally {
        if (active) setIsLoadingReports(false);
      }
    }

    void loadReports();
    return () => {
      active = false;
    };
  }, [selectedLocationId]);

  useEffect(() => {
    const reportId = selectedReportId;
    if (typeof reportId !== "number") return;

    let active = true;

    async function loadDetail(reportToLoad: number) {
      try {
        const detail = await getSquareSalesReport(reportToLoad);
        if (active) setReportDetail(detail);
      } catch {
        if (active) {
          setReportDetail(null);
          setDetailError(true);
        }
      } finally {
        if (active) setIsLoadingDetail(false);
      }
    }

    void loadDetail(reportId);
    return () => {
      active = false;
    };
  }, [selectedReportId]);

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setImportError(null);
    setImportResult(null);

    if (!selectedLocationId) {
      setImportError("Choose a location before importing a report.");
      return;
    }
    if (!rawReportText.trim()) {
      setImportError("Paste the full Square Sales Report text before importing.");
      return;
    }

    setIsImporting(true);
    try {
      const result = await importSquareSalesReport(
        Number(selectedLocationId),
        rawReportText,
      );
      setImportResult(result);
      setRawReportText("");
      setIsLoadingDetail(true);
      setDetailError(false);
      setReportDetail(null);
      setSelectedReportId(result.report_id);
      try {
        const refreshedReports = sortReports(
          await getSquareSalesReports(Number(selectedLocationId)),
        );
        setReports(refreshedReports);
        setReportsError(false);
      } catch {
        setReportsError(true);
      }
    } catch (error) {
      setImportError(getImportErrorMessage(error));
    } finally {
      setIsImporting(false);
    }
  }

  function handleLocationChange(locationId: string) {
    setSelectedLocationId(locationId);
    setImportError(null);
    setImportResult(null);
    setReports([]);
    setSelectedReportId(null);
    setReportDetail(null);
    setReportsError(false);
    setDetailError(false);
    setIsLoadingReports(Boolean(locationId));
    setIsLoadingDetail(false);
  }

  function handleSelectReport(reportId: number) {
    if (reportId === selectedReportId) return;
    setSelectedReportId(reportId);
    setReportDetail(null);
    setDetailError(false);
    setIsLoadingDetail(true);
  }

  const currency = selectedLocation?.currency ?? "USD";
  const report = reportDetail;
  const metrics = report
    ? [
        { label: "Gross Sales", amount: report.gross_sales_amount, prominent: true },
        { label: "Net Sales", amount: report.net_sales_amount, prominent: true },
        { label: "Total Collected", amount: report.total_collected_amount, prominent: true },
        { label: "Net Total", amount: report.net_total_amount, prominent: true },
        { label: "Returns", amount: report.returns_amount },
        { label: "Discounts & Comps", amount: report.discount_comp_amount },
        { label: "Refunds", amount: report.refund_amount },
        { label: "Fees", amount: report.fees_amount },
        { label: "Tax", amount: report.tax_amount },
        { label: "Tips", amount: report.tips_amount },
      ]
    : [];

  return (
    <main className="square-reports">
      <section className="square-reports-left" aria-label="Report import and history">
        <header className="square-reports-header">
          <p className="square-reports-eyebrow">Monthly performance</p>
          <h1>Square Sales Reports</h1>
          <p>
            Paste a Square Sales Report to import monthly sales, item, category,
            discount, fee, and refund performance into Ledger.
          </p>
        </header>

        <section className="square-report-panel square-report-import-panel">
          <div className="square-report-panel-heading">
            <div>
              <p className="square-reports-eyebrow">New import</p>
              <h2>Import a report</h2>
            </div>
            <span className="square-report-type">Aggregate report</span>
          </div>

          <p className="square-report-helper">
            This adds monthly report totals and performance rows. It does not
            create individual orders or payments.
          </p>

          {locationsError && (
            <p className="square-report-error" role="alert">
              Locations couldn&apos;t be loaded. Check your connection and try again.
            </p>
          )}

          <form className="square-report-import-form" onSubmit={handleImport}>
            <label htmlFor="square-report-location">Location</label>
            <select
              id="square-report-location"
              value={selectedLocationId}
              onChange={(event) => handleLocationChange(event.target.value)}
              disabled={isLoadingLocations || locations.length === 0}
              required
            >
              <option value="">
                {isLoadingLocations
                  ? "Loading locations..."
                  : locations.length === 0
                    ? "No active locations"
                    : "Choose a location"}
              </option>
              {locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name}
                </option>
              ))}
            </select>

            <label htmlFor="square-report-text">Square Sales Report text</label>
            <textarea
              id="square-report-text"
              value={rawReportText}
              onChange={(event) => setRawReportText(event.target.value)}
              placeholder="Paste the complete Square Sales Report email text here..."
              rows={14}
              spellCheck={false}
              disabled={isImporting}
              required
            />

            {importError && (
              <p className="square-report-error" role="alert">
                {importError}
              </p>
            )}

            <button
              className="square-report-primary-button"
              type="submit"
              disabled={
                isImporting ||
                isLoadingLocations ||
                !selectedLocationId ||
                !rawReportText.trim()
              }
            >
              {isImporting ? "Validating & importing..." : "Validate & Import"}
            </button>
          </form>

          {importResult && (
            <div className="square-report-import-success" role="status">
              <strong>
                {formatDate(importResult.report_start)} –{" "}
                {formatDate(importResult.report_end)} report imported successfully.
              </strong>
              <p>
                {importResult.categories_imported} categories ·{" "}
                {importResult.items_imported} items ·{" "}
                {importResult.discounts_imported} discounts
              </p>
              {importResult.warnings.length > 0 && (
                <ul className="square-report-warnings">
                  {importResult.warnings.map((warning, index) => (
                    <li key={`${index}-${warning}`}>{warning}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>

        <section className="square-report-panel square-report-history">
          <div className="square-report-panel-heading">
            <div>
              <p className="square-reports-eyebrow">Saved reports</p>
              <h2>Import history</h2>
            </div>
            {selectedLocation && (
              <span className="square-report-location-chip">
                {selectedLocation.name}
              </span>
            )}
          </div>

          {!selectedLocationId && (
            <p className="square-report-empty-inline">
              Select a location to view its imported reports.
            </p>
          )}
          {isLoadingReports && (
            <p className="square-report-empty-inline" role="status">
              Loading report history...
            </p>
          )}
          {reportsError && (
            <p className="square-report-error" role="alert">
              Report history couldn&apos;t be loaded. Please try again.
            </p>
          )}
          {!isLoadingReports &&
            !reportsError &&
            selectedLocationId &&
            reports.length === 0 && (
              <p className="square-report-empty-inline">
                No reports imported for this location yet.
              </p>
            )}
          {!isLoadingReports && reports.length > 0 && (
            <ul className="square-report-history-list">
              {reports.map((historyReport) => (
                <li key={historyReport.id}>
                  <button
                    className={`square-report-history-item${selectedReportId === historyReport.id ? " is-selected" : ""}`}
                    type="button"
                    onClick={() => handleSelectReport(historyReport.id)}
                    aria-pressed={selectedReportId === historyReport.id}
                  >
                    <span className="square-report-history-period">
                      {formatDate(historyReport.report_start)} –{" "}
                      {formatDate(historyReport.report_end)}
                    </span>
                    <span className="square-report-history-totals">
                      <span>Net sales {formatMoney(historyReport.net_sales_amount, currency)}</span>
                      <span>Collected {formatMoney(historyReport.total_collected_amount, currency)}</span>
                    </span>
                    <span className="square-report-history-imported">
                      Imported {formatDateTime(historyReport.created_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </section>

      <section
        className="square-reports-detail-column"
        aria-label="Selected Square report details"
      >
        {isLoadingDetail && (
          <div className="square-report-panel square-report-detail-state" role="status">
            Loading report details...
          </div>
        )}
        {detailError && (
          <div className="square-report-panel square-report-detail-state square-report-error">
            This report&apos;s details couldn&apos;t be loaded. Select it again or try later.
          </div>
        )}
        {!report && !isLoadingDetail && !detailError && (
          <div className="square-report-panel square-report-detail-empty">
            <span className="square-report-empty-icon" aria-hidden="true">
              SR
            </span>
            <h2>Monthly performance, all in one place</h2>
            <p>
              Import or select a Square Sales Report to view its financial
              metrics, category performance, item sales, and discounts.
            </p>
          </div>
        )}

        {report && !isLoadingDetail && (
          <div className="square-report-detail">
            <section className="square-report-panel square-report-overview">
              <div>
                <p className="square-reports-eyebrow">Report overview</p>
                <h2>{report.report_name ?? "Square Sales Report"}</h2>
                <p>Monthly aggregate report. This source does not contain day-level transaction detail.</p>
                <p className="square-report-overview-period">
                  {formatDate(report.report_start)} – {formatDate(report.report_end)}
                </p>
              </div>
              <dl className="square-report-metadata">
                <div>
                  <dt>Source</dt>
                  <dd>Square Sales Report</dd>
                </div>
                <div>
                  <dt>Location</dt>
                  <dd>{selectedLocation?.name ?? "Selected location"}</dd>
                </div>
                <div>
                  <dt>Reported</dt>
                  <dd>{formatDateTime(report.reported_at)}</dd>
                </div>
                <div>
                  <dt>Imported</dt>
                  <dd>{formatDateTime(report.created_at)}</dd>
                </div>
              </dl>
            </section>

            <section className="square-report-metrics-section">
              <div className="square-report-section-heading">
                <div>
                  <p className="square-reports-eyebrow">Sales snapshot</p>
                  <h2>Key metrics</h2>
                </div>
              </div>
              <div className="square-report-metrics">
                {metrics.map((metric) => (
                  <article
                    className={`square-report-metric${metric.prominent ? " is-prominent" : ""}`}
                    key={metric.label}
                  >
                    <p>{metric.label}</p>
                    <strong>{formatMoney(metric.amount, currency)}</strong>
                  </article>
                ))}
              </div>
            </section>

            <section className="square-report-panel">
              <div className="square-report-section-heading">
                <div>
                  <p className="square-reports-eyebrow">By menu category</p>
                  <h2>Category Sales</h2>
                </div>
                <span className="square-report-row-count">
                  {report.category_sales.length} categories
                </span>
              </div>
              {report.category_sales.length === 0 ? (
                <p className="square-report-empty-inline">
                  This report didn&apos;t include category sales rows.
                </p>
              ) : (
                <div className="square-report-data-list">
                  {report.category_sales.map((category) => (
                    <div className="square-report-data-row" key={category.id}>
                      <strong>{category.category_name}</strong>
                      <span>{formatQuantity(category.quantity)} sold</span>
                      <b>{formatMoney(category.sales_amount, currency)}</b>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="square-report-panel">
              <div className="square-report-section-heading">
                <div>
                  <p className="square-reports-eyebrow">By menu item</p>
                  <h2>Item Sales</h2>
                </div>
                <span className="square-report-row-count">
                  {report.item_sales.length} items
                </span>
              </div>
              {report.item_sales.length === 0 ? (
                <p className="square-report-empty-inline">
                  This report didn&apos;t include item sales rows.
                </p>
              ) : (
                <div className="square-report-data-list">
                  {report.item_sales.map((item) => (
                    <div className="square-report-data-row" key={item.id}>
                      <span className="square-report-item-name">
                        <strong>{item.item_name}</strong>
                        {item.variation_name && (
                          <small>{item.variation_name}</small>
                        )}
                      </span>
                      <span>{formatQuantity(item.quantity)} sold</span>
                      <b>{formatMoney(item.sales_amount, currency)}</b>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="square-report-panel">
              <div className="square-report-section-heading">
                <div>
                  <p className="square-reports-eyebrow">Applied during period</p>
                  <h2>Discounts Applied</h2>
                </div>
                <span className="square-report-row-count">
                  {report.discount_summaries.length} discounts
                </span>
              </div>
              {report.discount_summaries.length === 0 ? (
                <p className="square-report-empty-inline">
                  This report didn&apos;t include discount details.
                </p>
              ) : (
                <div className="square-report-data-list">
                  {report.discount_summaries.map((discount) => (
                    <div className="square-report-data-row" key={discount.id}>
                      <strong>{discount.discount_name}</strong>
                      <span>{discount.usage_count.toLocaleString()} uses</span>
                      <b>{formatMoney(discount.amount, currency)}</b>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </section>
    </main>
  );
};

export default SquareReports;
