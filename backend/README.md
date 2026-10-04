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

## Stop the server

Press `Ctrl+C` in the terminal where Uvicorn is running.
