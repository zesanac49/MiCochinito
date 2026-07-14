#!/usr/bin/env bash
# Despliegue: build + up + (migraciones y seed admin corren en el entrypoint).
# Uso:  ./deploy.sh
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f .env ]; then
  echo "[deploy] Creando .env desde .env.example (¡edita los secretos!)"
  cp .env.example .env
fi

# Puerto configurado (para el mensaje final).
PORT="$(grep -E '^APP_PORT=' .env | cut -d= -f2)"; PORT="${PORT:-8090}"

echo "[deploy] Construyendo y levantando servicios (mysql + app)..."
docker compose up -d --build

echo "[deploy] Esperando a que la app esté saludable..."
for _ in $(seq 1 40); do
  if docker compose exec -T app python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)" 2>/dev/null; then
    OK=1; break
  fi
  sleep 3
done

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
if [ "${OK:-0}" = "1" ]; then
  echo "[deploy] ¡Listo!"
else
  echo "[deploy] La app tardó en responder. Revisa: docker compose logs -f app"
fi
echo "  App:     http://${IP:-localhost}:${PORT}"
echo "  Swagger: http://${IP:-localhost}:${PORT}/api/v1/docs"
echo "  Admin:   el de ADMIN_EMAIL / ADMIN_PASSWORD de tu .env"
