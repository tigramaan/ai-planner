#!/bin/sh
set -eu

until alembic upgrade head; do
  echo "Database is not ready; retrying migration in 3 seconds" >&2
  sleep 3
done

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
