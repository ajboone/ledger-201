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

## Load Sushi 201 demo orders

From the `backend` directory, run:

```bash
python -m app.demo.seed
```

This opt-in command creates or reuses the Sushi 201 location and inserts four
dated demo orders with realistic line items, five payments, and three refunds.
The demo includes completed and failed payments plus completed, pending, and
failed refunds. Stable Square-style IDs prevent duplicate records on reruns;
existing records are reused, and the command does not delete or reset
developer data. To target a separate SQLite database, pass
`--database-url sqlite:///./demo-ledger201.db`.

Timestamps continue to use timezone-aware Python datetimes, but SQLite may
discard timezone offsets when values are read back. Reconciliation must
normalize timestamps to a documented timezone convention before time-window
matching. `create_all()` creates these new tables but does not migrate
previously existing tables.

## Stop the server

Press `Ctrl+C` in the terminal where Uvicorn is running.
