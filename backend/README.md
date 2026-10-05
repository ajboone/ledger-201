# Ledger 201 Backend

The Ledger 201 backend is a FastAPI application for managing restaurant
expenses and purchasing. It uses SQLAlchemy for database access and SQLite for
local data storage.

## Technology

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Uvicorn

## Project structure

```text
backend/
|-- app/
|   |-- __init__.py
|   |-- database.py
|   |-- main.py
|   |-- models.py
|   |-- demo/
|   |   `-- seed.py
|   |-- routers/
|   `-- services/
|       `-- orders.py
|-- ledger201.db
`-- README.md
```

- `app/main.py` creates the FastAPI application and registers API routers.
- `app/database.py` configures the SQLite connection and database sessions.
- `app/models.py` contains the SQLAlchemy database models.
- `app/services/orders.py` owns reusable order-creation persistence logic.
- `app/demo/seed.py` provides the opt-in Sushi 201 demo-data command.
- `ledger201.db` is the local SQLite database.

## Setup

From the repository root, create and activate a virtual environment if one is
not already active:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On Git Bash:

```bash
source .venv/Scripts/activate
```

Install the project dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the API

Change into the backend directory and start the development server:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

The API will be available at:

- API: `http://127.0.0.1:8000`
- Interactive documentation: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

## Available endpoint

### `GET /`

Confirms that the API is running.

Example response:

```json
{
  "message": "Ledger 201 is running."
}
```

## Database

The application connects to `ledger201.db` through the following SQLite URL:

```text
sqlite:///./ledger201.db
```

Because this path is relative, run Uvicorn from the `backend` directory. The
application creates any missing tables when it starts.

The current schema includes `vendors`, `locations`, `orders`, and
`order_line_items`, `payments`, and `refunds` tables. The transaction domain
includes:

- `vendors`: supplier records for purchasing data
- `locations`: restaurant location data
- `orders`: normalized order totals and metadata with a unique Square order ID
  when present
- `order_line_items`: nested line items for menu and sales analysis
- `payments`: payment amount applied to an order, excluding tips and processor
  fees; only `COMPLETED` payments represent collected funds
- `refunds`: refund amounts against a payment; multiple partial refunds are
  supported, and only `COMPLETED` refunds represent returned funds

Order, payment, and refund monetary amounts use integer minor currency units
and retain Square external identifiers needed for later synchronization.
Refund validation reserves the total of `COMPLETED` and `PENDING` refunds
against the payment amount; `FAILED` refunds do not count toward that limit.
Refunds can be recorded only against completed payments.

## Payment and refund API

- `POST /api/payments` and `GET /api/payments`
- `GET /api/payments/{payment_id}`
- `POST /api/refunds` and `GET /api/refunds`
- `GET /api/refunds/{refund_id}`

Payment listing supports `?order_id=<id>` and refund listing supports
`?payment_id=<id>`. Refund responses include a compact payment summary without
nested orders or refund collections.

## Daily Review

`GET /api/daily-review?location_id=<id>&date=YYYY-MM-DD` returns daily sales,
discounts, taxes, service charges, completed payment/refund totals, net
collected amount, average order value, per-order reconciliation, and ranked
item sales for the selected location and date.

Orders are grouped by their `created_at` local calendar date. Because SQLite
drops timezone offsets in the current timestamp columns, stored naive
timestamps are temporarily treated as location-local wall time. Payments and
refunds are included with their related Orders regardless of their own
creation dates. Reconciliation is completed payments minus completed refunds
minus order total; only `COMPLETED` payments and refunds count. The daily
status is `REVIEW_REQUIRED` if its difference is nonzero or any individual
Order is mismatched. Item sales use line-item `total_amount` after line
discounts and rank by quantity, then net item sales, then item name. The
review rejects Orders, Payments, or Refunds whose currency differs from the
currency of their parent record rather than combining incomparable amounts.
Average order value is order total divided by order count, rounded to the
nearest minor unit.

## Deterministic analyst endpoints

The read-only `/api/analyst` endpoints expose structured facts for later
analysis without using an LLM or changing ledger data:

- `GET /api/analyst/daily-summary?location_id=<id>&date=YYYY-MM-DD`
- `GET /api/analyst/reconciliation-exceptions?location_id=<id>&date=YYYY-MM-DD`
- `GET /api/analyst/top-items?location_id=<id>&date=YYYY-MM-DD&limit=5`
- `GET /api/analyst/refunds?location_id=<id>&date=YYYY-MM-DD`
- `GET /api/analyst/discounts?location_id=<id>&date=YYYY-MM-DD`
- `GET /api/analyst/compare?location_id=<id>&date_a=YYYY-MM-DD&date_b=YYYY-MM-DD`

Daily summaries and comparisons use the same integer-cent calculations,
location-local date boundaries, currency checks, and completed payment/refund
rules as Daily Review. Item rankings sort by quantity sold, then net item sales,
then case-insensitive item name (with exact item name as a final tie-breaker).
Refund totals include only completed refunds; pending and failed refunds are
reported separately. Comparison changes are date B minus date A, and
percentage changes are `null` when the date A denominator is zero.

## AI Analyst query

`POST /api/ai-analyst/query` accepts a question and a trusted location ID:

```json
{
  "question": "Why does September 14, 2026 require review?",
  "location_id": 1
}
```

The response contains an `answer` and a `tool_calls_used` trace. The model
receives only approved function tools backed by deterministic analyst
services; the application supplies the location ID, validates arguments, and
returns tool results in integer minor currency units. The model is instructed
to explain supplied results rather than recalculate them, distinguish facts
from possible explanations, and ask for missing dates instead of guessing.
Tool calls are limited to five iterations per request.

Configure `OPENAI_API_KEY` and `OPENAI_MODEL` in the backend process
environment or in `backend/.env` before using this endpoint. The backend loads
that file from a path derived from `app/config.py`, independent of the working
directory, without overriding values already supplied by the process
environment. No model default is assumed. Missing configuration returns HTTP
503. Provider or invalid model-tool responses return HTTP 502; unknown
locations return HTTP 404. Never expose API keys in client requests or
responses.

## Aggregate Square Sales Report imports

The first Square import path stores monthly sales-report aggregates. It does
not create or infer Orders, Payments, or Refunds. All monetary values are
stored as integer cents. Sign is preserved exactly as shown in the report:
parentheses or a leading minus sign become negative; unmarked values remain
positive. Discounts and fees are not converted to absolute values.

Endpoints:

- `POST /api/square-reports/import` with `location_id` and `raw_report_text`
- `GET /api/square-reports` with an optional `location_id` filter
- `GET /api/square-reports/{report_id}` for the summary and child sections

The importer requires a report date range and all listed core Sales and
Payments metrics. It parses optional Discounts Applied, Category Sales, and
Item Sales sections in both horizontal table-like text and Square's vertical
email layout (label, `× quantity`, amount). It ignores report metadata and
the optional Covers count, and retains quantities to four decimal places.
When an item row is immediately followed by a variation row with the same
quantity and amount, the importer stores one item row using the parent name
and the variation label; Square's repeated variation total is not stored as a
second sale. A repeated location/date period returns
HTTP 409 and does not overwrite the original import. Suspicious sales/net
total relationships are reported as warnings; source amounts are retained.
The parser is designed for labeled email-report text and is not a PDF, CSV, or
spreadsheet decoder.

Aggregate report data lives in `square_sales_reports`,
`square_category_sales`, `square_item_sales`, and
`square_discount_summaries`. Existing transaction models and analyst
calculations remain separate. `create_all()` creates these missing tables for
local development; it does not migrate existing tables.

## Load Sushi 201 demo orders

From the `backend` directory, run:

```bash
python -m app.demo.seed
```

This opt-in command creates or reuses the Sushi 201 location and inserts four
dated demo orders using fixed-price items and prices from the
[Sushi 201 Summerville menu](https://sushi201summerville.com/menu/18669103),
plus five payments and three refunds. The demo includes completed and failed
payments plus completed, pending, and failed refunds. Stable Square-style IDs
prevent duplicates. On reruns, matching seeded order fields and line items are
refreshed in place and seeded payment amounts are updated to match; all other
records are left alone. The seed refuses to rewrite a demo order if its
line-item count differs from the fixture. To target a separate SQLite database, pass
`--database-url sqlite:///./demo-ledger201.db`.

Menu prices are the listed base prices in cents; options, modifiers, and
additional charges are not represented. Demo tax is rounded to whole cents at
approximately 8% of the discounted subtotal. September 12 is the clean
reconciled example; September 14 keeps the existing completed partial refund,
so that day's order remains `REVIEW_REQUIRED`.

Timestamps continue to use timezone-aware Python datetimes, but SQLite may
discard timezone offsets when values are read back. Daily Review therefore
uses the documented local-wall-time rule above. `create_all()` creates missing
tables but does not migrate previously existing tables.

## Transaction provenance and local migration

`Order.provenance` is an explicit, constrained value: `demo`, `square_import`,
`manual`, or `unknown` (the default). Line items, payments, and refunds inherit
their parent Order's provenance; `Payment.source_type` still means payment
method (CARD/CASH), not provenance. Use `manual` only for explicitly verified
real manual entries and `square_import` for real transaction imports. The
presence of a Square ID does not establish provenance.

Before starting the updated app against an existing local SQLite database,
back up that database and run from `backend`:

```powershell
python -m app.migrate_provenance
python -m app.demo.seed
```

The migration is idempotent and marks all existing orders `unknown`, never
real. The seed then marks only its four exact reserved `LEDGER201-DEMO-ORDER-001`
through `004` fixtures as `demo`, preserving IDs, payments, refunds, and the
September 14 reconciliation exception. It refuses to overwrite a fixture
explicitly marked real. Arbitrary IDs, even those containing "demo", are not
classified. For a separate database, call `migrate(target_engine)` before
seeding it. New databases need no migration. `create_all()` alone cannot add
this column to existing tables.

Coverage separates real, demo, and unknown transactions by location. Legacy
`available_granularity` describes real data only; the explicit
`available_real_granularity` and `available_demo_granularity` fields distinguish
daily/transaction coverage. No reports means no monthly granularity.

AI daily tools require real provenance and filter every calculation to real
orders, including in mixed datasets. Demo chat analysis remains disabled;
use Daily Review (Demo) for synthetic analysis. The Daily Review page explicitly
requests `provenance=demo`; the backend retains its unfiltered calculation API
for compatibility and accepts an optional provenance filter. Coverage means
records exist, not that every day is complete. Monthly tools continue to use
imported Square aggregate reports.

Future real imports should set explicit Order provenance, after which coverage
and AI daily tools work without including demo rows. Adapt the Daily Review
label and filter together when adding a real-data mode. No Square API or
transaction importer is added here.

## Stop the server

Press `Ctrl+C` in the terminal where Uvicorn is running.
