#!/usr/bin/env bash
set -e

# Wait for Postgres, run migrations, then start the API server.
echo "Waiting for database..."
python - <<'PY'
import time, sqlalchemy
from app.config import settings
for attempt in range(30):
    try:
        eng = sqlalchemy.create_engine(settings.database_url)
        with eng.connect() as c:
            c.execute(sqlalchemy.text("SELECT 1"))
        print("Database is up.")
        break
    except Exception as exc:
        print(f"  db not ready ({attempt+1}/30): {exc}")
        time.sleep(2)
else:
    raise SystemExit("Database never became available")
PY

echo "Running migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
