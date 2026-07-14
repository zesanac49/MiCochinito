#!/usr/bin/env bash
# Entrypoint del contenedor app: espera MySQL, aplica migraciones, siembra el
# administrador inicial (idempotente) y arranca uvicorn + nginx vía supervisord.
set -euo pipefail

cd /app/backend
export PYTHONPATH=/app/backend

echo "[entrypoint] Esperando a que MySQL responda..."
python - <<'PY'
import os, time
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
ultimo = None
for _ in range(60):
    try:
        with create_engine(url).connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[entrypoint] MySQL disponible.")
        break
    except Exception as exc:  # noqa: BLE001
        ultimo = exc
        time.sleep(2)
else:
    raise SystemExit(f"[entrypoint] MySQL no respondió: {ultimo}")
PY

echo "[entrypoint] Aplicando migraciones (alembic upgrade head)..."
alembic upgrade head

echo "[entrypoint] Sembrando administrador inicial (idempotente)..."
python scripts/seed_admin.py || echo "[entrypoint] seed_admin omitido."

echo "[entrypoint] Arrancando uvicorn + nginx (supervisord)..."
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
