#!/usr/bin/env bash
# ============================================================
#  Actualiza el despliegue en el servidor: trae los cambios del
#  repo y reconstruye. Las migraciones se aplican solas al arrancar;
#  los datos de MySQL persisten en el volumen.
#  Uso:  ./update.sh
# ============================================================
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf "\n\033[1;36m[update]\033[0m %s\n" "$*"; }

PORT="$(grep -E '^APP_PORT=' .env 2>/dev/null | cut -d= -f2)"; PORT="${PORT:-8090}"

log "Trayendo cambios del repositorio (git pull)..."
git pull

log "Reconstruyendo y relanzando contenedores..."
docker compose up -d --build

log "Estado de los servicios:"
docker compose ps

log "Verificando health..."
if curl -fs "http://127.0.0.1:${PORT}/health" >/dev/null; then
  echo "  OK -> la aplicación responde en el puerto ${PORT}."
else
  echo "  Aún no responde; revisa: docker compose logs -f app"
fi

log "Actualización completada."
