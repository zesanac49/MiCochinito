# syntax=docker/dockerfile:1

# ============================================================
#  Stage 1 — Build del frontend (Vite + React)
# ============================================================
FROM node:20-alpine AS frontend-build
WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
# El cliente Axios usa /api/v1 relativo: detrás de nginx no necesita URL absoluta.
RUN npm run build


# ============================================================
#  Stage 2 — Runtime: backend (uvicorn) + nginx (supervisord)
#  Python 3.11-slim: el stack está congelado en 3.12 pero se evita
#  sintaxis 3.12 (PEP 695) y el entorno de referencia es 3.11.
# ============================================================
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Dependencias Python (producción) ---
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# --- Código backend (incluye alembic.ini + migraciones) ---
COPY backend/ /app/backend/

# --- Frontend compilado ---
COPY --from=frontend-build /build/dist /var/www/html

# --- Configuración nginx / supervisor / entrypoint ---
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod +x /app/docker/entrypoint.sh

ENV PYTHONPATH=/app/backend

EXPOSE 8080

ENTRYPOINT ["/app/docker/entrypoint.sh"]
