# Granite API

Standalone FastAPI service alongside `granite-web`. Phase 1 persists quote requests in PostgreSQL. The API retains the frontend contract: `POST /api/v1/leads` accepts `name`, `phone`, `service_slug`, `message`, `area`, `stone_type`, and `expected_size`.

## Run locally with Docker Compose

Requires Docker Desktop.

```powershell
docker compose up --build
```

This starts PostgreSQL and the API. PostgreSQL data is stored in the named `postgres_data` volume. Stop the containers with `Ctrl+C`; use `docker compose down` to stop them later. Do not run `docker compose down -v` unless you intend to delete the database volume.

API docs: <http://localhost:8000/docs> · health and database check: <http://localhost:8000/health>

The frontend can keep using `NEXT_PUBLIC_API_URL=http://localhost:8000`.

## Run the API directly with Python

Start just the PostgreSQL service first:

```powershell
docker compose up -d db
```

Then in another terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --env-file .env
```

The local `.env` uses the mapped `localhost:5432` address. Set `DATABASE_URL` to the PostgreSQL connection string supplied by your host in deployment, and set `CORS_ORIGINS` to the exact frontend origin(s). Keep database credentials in deployment secrets; do not commit them.

## Database schema

The current starter creates the `leads` table on API startup with SQLAlchemy metadata. Before production schema changes, add Alembic migrations and a managed PostgreSQL backup/restore policy. The previous SQLite file, if present, is not automatically imported; migrate any leads you need to keep before switching.

This starter does not yet include rate limiting, human verification, consent/retention workflow, or lead notifications; add those before public production use.
