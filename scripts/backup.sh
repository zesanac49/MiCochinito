#!/usr/bin/env bash
# Respaldo de la base de datos de Natillera (mysqldump del contenedor).
# Uso:  ./scripts/backup.sh [carpeta_destino]
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DEST="${1:-backups}"
mkdir -p "$DEST"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVO="${DEST}/natillera-${STAMP}.sql"

# Credenciales desde .env
DB="$(grep -E '^MYSQL_DATABASE=' .env | cut -d= -f2)"
ROOTP="$(grep -E '^MYSQL_ROOT_PASSWORD=' .env | cut -d= -f2)"

echo "[backup] Generando $ARCHIVO ..."
docker compose exec -T mysql sh -c "exec mysqldump -uroot -p'${ROOTP}' --single-transaction --routines '${DB}'" > "$ARCHIVO"
echo "[backup] Listo: $ARCHIVO"
