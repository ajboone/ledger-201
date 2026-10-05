import { useEffect, useState } from "react";
import { getDailyReview } from "../api/dailyReview";
import { getLocations } from "../api/locations";
import type { DailyReview as DailyReviewData } from "../types/dailyReview";
import type { Location } from "../types/location";
import { formatMoney } from "../utils/formatMoney";
import "./DailyReview.css";

function localToday(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const DailyReview = () => {
  const [locations, setLocations] = useState<Location[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState("");
  const [reviewDate, setReviewDate] = useState(localToday);
  const [review, setReview] = useState<DailyReviewData | null>(null);
  const [isLoadingLocations, setIsLoadingLocations] = useState(true);
  const [isLoadingReview, setIsLoadingReview] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadLocations() {
      try {
        const locationData = await getLocations();
        if (!active) return;
        setLocations(locationData);
        if (locationData.length > 0) {
          setIsLoadingReview(true);
          setSelectedLocationId(String(locationData[0].id));
        }
      } catch (error) {
        if (active) {
          setErrorMessage(
            error instanceof Error ? error.message : "Unable to load locations.",
          );
        }
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
    if (!selectedLocationId || !reviewDate) {
      return;
    }

    let active = true;

    async function loadReview() {
      try {
        const reviewData = await getDailyReview(
          Number(selectedLocationId),
          reviewDate,
        );
        if (active) {
          setReview(reviewData);
          setIsLoadingReview(false);
        }
      } catch (error) {
        if (active) {
          setReview(null);
          setIsLoadingReview(false);
          setErrorMessage(
            error instanceof Error ? error.message : "Unable to load daily review.",
          );
        }
      }
    }

    void loadReview();
    return () => {
      active = false;
    };
  }, [selectedLocationId, reviewDate]);

  const currency = review?.currency ?? "USD";
  const metrics = review
    ? [
        { label: "Orders", value: review.order_count.toLocaleString() },
        { label: "Order total", value: formatMoney(review.order_total_amount, currency) },
        { label: "Average order", value: formatMoney(review.average_order_value, currency) },
        { label: "Discounts", value: formatMoney(review.discount_amount, currency) },
        { label: "Refunds", value: formatMoney(review.completed_refund_amount, currency) },
        { label: "Net collected", value: formatMoney(review.net_collected_amount, currency) },
        { label: "Tax", value: formatMoney(review.tax_amount, currency) },
        { label: "Service charges", value: formatMoney(review.service_charge_amount, currency) },
      ]
    : [];

  return (
    <main className="daily-review">
      <header className="daily-review-header">
        <div>
          <p className="daily-review-eyebrow">Restaurant operations</p>
          <h1>Daily Review (Demo)</h1>
          <p>Review sales, collected payments, refunds, and order variances.</p>
        </div>
        <div className="daily-review-filters">
          <label>
            Location
            <select
              value={selectedLocationId}
              onChange={(event) => {
                setReview(null);
                setErrorMessage(null);
                setIsLoadingReview(Boolean(event.target.value && reviewDate));
                setSelectedLocationId(event.target.value);
              }}
              disabled={isLoadingLocations || locations.length === 0}
            >
              {locations.length === 0 && <option value="">No locations</option>}
              {locations.map((location) => (
                <option key={location.id} value={location.id}>
                  {location.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Review date
            <input
              type="date"
              value={reviewDate}
              onChange={(event) => {
                setReview(null);
                setErrorMessage(null);
                setIsLoadingReview(Boolean(selectedLocationId && event.target.value));
                setReviewDate(event.target.value);
              }}
            />
          </label>
        </div>
      </header>
      <aside className="daily-review-demo-notice" aria-label="Demo data">
        <strong>Demo data</strong>
        <p>This view uses synthetic transaction data for development. Real day-level analysis will be enabled once transaction-level Square data is connected.</p>
      </aside>

      {isLoadingLocations && <p role="status">Loading locations...</p>}
      {isLoadingReview && <p role="status">Calculating daily review...</p>}
      {errorMessage && (
        <p className="daily-review-error" role="alert">
          Unable to load daily review: {errorMessage}
        </p>
      )}
      {!isLoadingLocations && locations.length === 0 && !errorMessage && (
        <p className="daily-review-empty">Create a location to begin a daily review.</p>
      )}
      {review && !isLoadingReview && (
        <>
          <section className="daily-review-metrics" aria-label="Daily summary">
            {metrics.map((metric) => (
              <article className="daily-review-card" key={metric.label}>
                <p>{metric.label}</p>
                <strong>{metric.value}</strong>
              </article>
            ))}
          </section>

          <section className="daily-review-panel">
            <div className="daily-review-section-heading">
              <div>
                <p className="daily-review-eyebrow">Payments minus refunds vs orders</p>
                <h2>Reconciliation</h2>
              </div>
              <span
                className={`review-status ${review.reconciliation_status === "RECONCILED" ? "is-reconciled" : "needs-review"}`}
              >
                {review.reconciliation_status === "RECONCILED"
                  ? "Reconciled"
                  : "Review required"}
              </span>
            </div>
            <p className="daily-review-difference">
              Daily difference:{" "}
              <strong>
                {formatMoney(review.reconciliation_difference, review.currency)}
              </strong>
            </p>
            {review.orders.length === 0 ? (
              <p className="daily-review-empty">No orders for this date.</p>
            ) : (
              <div className="daily-review-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Order</th>
                      <th>Order total</th>
                      <th>Paid</th>
                      <th>Refunded</th>
                      <th>Net collected</th>
                      <th>Difference</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {review.orders.map((order) => (
                      <tr
                        className={order.status === "REVIEW_REQUIRED" ? "review-row" : ""}
                        key={order.order_id}
                      >
                        <td>{order.square_order_id ?? `Order ${order.order_id}`}</td>
                        <td>{formatMoney(order.order_total_amount, currency)}</td>
                        <td>{formatMoney(order.completed_payment_amount, currency)}</td>
                        <td>{formatMoney(order.completed_refund_amount, currency)}</td>
                        <td>{formatMoney(order.net_collected_amount, currency)}</td>
                        <td>{formatMoney(order.difference, currency)}</td>
                        <td>
                          <span
                            className={`review-status ${order.status === "RECONCILED" ? "is-reconciled" : "needs-review"}`}
                          >
                            {order.status === "RECONCILED" ? "Reconciled" : "Review"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="daily-review-panel">
            <div className="daily-review-section-heading">
              <div>
                <p className="daily-review-eyebrow">By item</p>
                <h2>Top Items</h2>
              </div>
              <span className="daily-review-muted">Ranked by quantity sold</span>
            </div>
            {review.top_items.length === 0 ? (
              <p className="daily-review-empty">No item sales for this date.</p>
            ) : (
              <div className="daily-review-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>Quantity sold</th>
                      <th>Gross sales</th>
                      <th>Net item sales</th>
                    </tr>
                  </thead>
                  <tbody>
                    {review.top_items.map((item) => (
                      <tr key={item.item_name}>
                        <td>{item.item_name}</td>
                        <td>{item.quantity_sold}</td>
                        <td>{formatMoney(item.gross_sales_amount, currency)}</td>
                        <td>{formatMoney(item.total_sales_amount, currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
};

export default DailyReview;
