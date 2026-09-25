# Granite API

Standalone FastAPI service alongside `granite-web`. `POST /api/v1/leads` accepts lead details and a `turnstile_token` from the quote form.

## Run locally with Docker Compose

Requires Docker Desktop.

```powershell
Copy-Item .env.example .env
# Replace POSTGRES_PASSWORD and RATE_LIMIT_SALT in .env with private values.
docker compose up --build
```

This starts PostgreSQL and the API. PostgreSQL data is stored in the named `postgres_data` volume. Stop the containers with `Ctrl+C`; use `docker compose down` to stop them later. Do not run `docker compose down -v` unless you intend to delete the database volume.

API docs: <http://localhost:8001/docs>; liveness: <http://localhost:8001/health>; database readiness: <http://localhost:8001/ready>.

Set the frontend to `NEXT_PUBLIC_API_URL=http://localhost:8001`. Change `API_PORT` in the API `.env` if port 8001 is also occupied.

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
uvicorn app.main:app --reload --env-file .env
```

The local `.env` uses the mapped `localhost:55432` address. Set `DATABASE_URL` to the PostgreSQL connection string supplied by your host in deployment, and set `CORS_ORIGINS` to the exact frontend origin(s). Keep database credentials in deployment secrets; do not commit them.

## Database schema

The app creates `leads` and `rate_limit_buckets` at startup. Rate limits allow five requests per IP per ten-minute bucket and use a salted IP hash. Turnstile validation runs before a lead is saved. Before future schema changes, add Alembic migrations. The previous SQLite file, if present, is not imported automatically.

The API does not log submitted contact details. The retention target is 180 days. Run `python -m app.maintenance` monthly to preview expired rows, then `python -m app.maintenance --apply` to remove them after review. Handle early deletion requests by finding the relevant lead in Neon and deleting it. Export encrypted backups outside Neon with `pg_dump` at least monthly and test a restore; the free services do not schedule this for you. Keep backup copies under the same retention policy.

## Deploy on Render Free with Neon Free Postgres

1. Create a Neon project and copy its **pooled** connection string. Replace the URL scheme with `postgresql+psycopg://` and retain the `sslmode=require` query parameter. Never put this URL in the frontend or commit it to Git.
2. Create a Cloudflare Turnstile widget limited to the production frontend hostname. Keep its secret key private; copy its public site key for the frontend.
3. In Render, create a Blueprint from this repository. Enter `DATABASE_URL`, `CORS_ORIGINS` (the exact HTTPS frontend origin), `TURNSTILE_SECRET_KEY`, and `TURNSTILE_HOSTNAME` (hostname only, without `https://`). Render generates `RATE_LIMIT_SALT`. The Docker command uses Render's `PORT`.
4. Check `/health` for liveness and `/ready` for database connectivity. Set `NEXT_PUBLIC_API_URL` to the HTTPS Render URL and `NEXT_PUBLIC_TURNSTILE_SITE_KEY` to the public site key in the frontend deployment, then redeploy it.
5. Submit a test lead and verify it appears in Neon. Confirm missing/invalid Turnstile tokens are rejected, and six requests from one IP in ten minutes produce a `429`.

Render Free sleeps when idle, so the first form submission after a quiet period can be slow. `/health` does not query Neon, allowing its compute to sleep. Use Cloudflare's documented test site/secret keys only for local development. The local Docker Compose database is not part of the production deployment.
