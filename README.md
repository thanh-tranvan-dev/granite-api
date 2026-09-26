# Granite API

Standalone FastAPI service alongside `granite-web`. `POST /api/v1/leads` accepts lead details and a `turnstile_token` from the quote form.

## Run locally with Docker Compose

Requires Docker Desktop.

```powershell
Copy-Item .env.development.example .env.development
# Set private local values in .env.development.
docker compose --env-file .env.development up --build
```

This starts PostgreSQL and the API. PostgreSQL data is stored in the named `postgres_data` volume. Stop the containers with `Ctrl+C`; use `docker compose --env-file .env.development down` to stop them later. Do not run `docker compose --env-file .env.development down -v` unless you intend to delete the local database volume.

API docs: <http://localhost:8001/docs>; liveness: <http://localhost:8001/health>; database readiness: <http://localhost:8001/ready>.

Set the frontend to `NEXT_PUBLIC_API_URL=http://localhost:8001`. Change `API_PORT` in `.env.development` if port 8001 is occupied. Compose builds its internal database URL using `POSTGRES_PASSWORD` and the `db:5432` service address; direct Python runs use `DATABASE_URL` (`localhost:55432`).

## Run the API directly with Python

Start just the PostgreSQL service first:

```powershell
docker compose --env-file .env.development up -d db
```

Then in another terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --env-file .env.development
```

For production, create `.env.production` from `.env.production.example` when running the API directly. It points to the Supabase Session pooler. On Render, enter those production values in the service's environment settings; do not upload or commit `.env.production`.

## Database schema

The app creates `leads` and `rate_limit_buckets` at startup. Rate limits allow five requests per IP per ten-minute bucket and use a salted IP hash. Turnstile validation runs before a lead is saved. Before future schema changes, add Alembic migrations. The previous SQLite file, if present, is not imported automatically.

After a lead is saved, the API sends a one-way Telegram notification when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured. Telegram errors are logged without changing the successful lead response. Keep the bot token in the API environment only.

The API does not log submitted contact details. The retention target is 180 days. Run `python -m app.maintenance` monthly to preview expired rows, then `python -m app.maintenance --apply` to remove them after review. Handle early deletion requests by finding the relevant lead in Supabase and deleting it. Export encrypted backups outside Supabase with `pg_dump` at least monthly and test a restore; the free services do not schedule this for you. Keep backup copies under the same retention policy.

## Deploy on Render with Supabase Postgres

1. Create a Supabase project and copy its **Session pooler** connection string. Replace the URL scheme with `postgresql+psycopg://` and retain the `sslmode=require` query parameter. Never put this URL in the frontend or commit it to Git.
2. Create a Cloudflare Turnstile widget limited to the production frontend hostname. Keep its secret key private; copy its public site key for the frontend.
3. In Render, create a Blueprint from this repository. Enter `DATABASE_URL`, `CORS_ORIGINS` (the exact HTTPS frontend origin), `TURNSTILE_SECRET_KEY`, `TURNSTILE_HOSTNAME` (hostname only, without `https://`), `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID`. Render generates `RATE_LIMIT_SALT`. The Docker command uses Render's `PORT`.
4. Check `/health` for liveness and `/ready` for database connectivity. Set `NEXT_PUBLIC_API_URL` to the HTTPS Render URL and `NEXT_PUBLIC_TURNSTILE_SITE_KEY` to the public site key in the frontend deployment, then redeploy it.
5. Submit a test lead and verify it appears in Supabase. Confirm missing/invalid Turnstile tokens are rejected, and six requests from one IP in ten minutes produce a `429`.

Render Free sleeps when idle, so the first form submission after a quiet period can be slow. `/health` does not query Supabase. Use Cloudflare's documented test site/secret keys only for local development. Docker Compose uses its own local PostgreSQL database; production uses Supabase and is configured separately in Render.
