#!/usr/bin/env bash
# Restaura un respaldo SQL en la base de datos de Natillera.
# Uso:  ./scripts/restore.sh backups/natillera-YYYYMMDD-HHMMSS.sql
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ARCHIVO="${1:?Indica el archivo .sql a restaurar}"
[ -f "$ARCHIVO" ] || { echo "No existe: $ARCHIVO"; exit 1; }

DB="$(grep -E '^MYSQL_DATABASE=' .env | cut -d= -f2)"
ROOTP="$(grep -E '^MYSQL_ROOT_PASSWORD=' .env | cut -d= -f2)"

echo "[restore] Restaurando $ARCHIVO en la BD '${DB}' ..."
docker compose exec -T mysql sh -c "exec mysql -uroot -p'${ROOTP}' '${DB}'" < "$ARCHIVO"
echo "[restore] Restauración completada."
