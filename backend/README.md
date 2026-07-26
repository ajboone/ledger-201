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
|   `-- models.py
|-- ledger201.db
`-- README.md
```

- `app/main.py` creates the FastAPI application and defines API routes.
- `app/database.py` configures the SQLite connection and database sessions.
- `app/models.py` contains the SQLAlchemy database models.
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

The current schema includes a `vendors` table with:

- `id`: unique vendor identifier
- `name`: unique vendor name, limited to 100 characters
- `created_at`: timestamp assigned when the vendor is created

## Stop the server

Press `Ctrl+C` in the terminal where Uvicorn is running.
