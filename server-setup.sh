#!/usr/bin/env bash
# ============================================================
#  Natillera — instala Docker y despliega en un servidor Linux
#  (Ubuntu / Debian). Idempotente: puedes re-ejecutarlo.
#  Acceso en la red local por  http://IP_DEL_SERVIDOR:APP_PORT
#
#  Uso:
#    chmod +x server-setup.sh
#    ./server-setup.sh
# ============================================================
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log()  { printf "\n\033[1;36m[setup]\033[0m %s\n" "$*"; }
warn() { printf "\n\033[1;33m[aviso]\033[0m %s\n" "$*"; }

if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo"; fi

# ------------------------------------------------------------
# 1) Instalar Docker Engine + Compose (si falta)
# ------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "Instalando Docker Engine + Compose plugin..."
  . /etc/os-release
  DISTRO="${ID:-ubuntu}"
  CODENAME="${VERSION_CODENAME:-stable}"

  $SUDO apt-get update
  $SUDO apt-get install -y ca-certificates curl git openssl
  $SUDO install -m 0755 -d /etc/apt/keyrings
  $SUDO curl -fsSL "https://download.docker.com/linux/${DISTRO}/gpg" -o /etc/apt/keyrings/docker.asc
  $SUDO chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${DISTRO} ${CODENAME} stable" \
    | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null
  $SUDO apt-get update
  $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  $SUDO usermod -aG docker "$USER" || true
  warn "Docker instalado. Para usarlo sin 'sudo' cierra sesión y vuelve a entrar (o: newgrp docker)."
else
  log "Docker ya está instalado: $(docker --version)"
fi

DOCKER="docker"
if ! docker info >/dev/null 2>&1; then DOCKER="$SUDO docker"; fi

# ------------------------------------------------------------
# 2) Preparar .env con secretos aleatorios (si no existe)
# ------------------------------------------------------------
if [ ! -f .env ]; then
  log "Creando .env desde .env.example con secretos aleatorios..."
  cp .env.example .env
  command -v openssl >/dev/null 2>&1 || $SUDO apt-get install -y openssl
  JWT="$(openssl rand -hex 32)"
  DBP="$(openssl rand -hex 16)"
  ROOTP="$(openssl rand -hex 16)"
  ADMP="$(openssl rand -hex 12)"
  sed -i "s/^ENTORNO=.*/ENTORNO=prod/" .env
  sed -i "s/^DEBUG=.*/DEBUG=false/" .env
  sed -i "s#^JWT_SECRET=.*#JWT_SECRET=${JWT}#" .env
  sed -i "s/^MYSQL_PASSWORD=.*/MYSQL_PASSWORD=${DBP}/" .env
  sed -i "s/^MYSQL_ROOT_PASSWORD=.*/MYSQL_ROOT_PASSWORD=${ROOTP}/" .env
  sed -i "s/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=${ADMP}/" .env
  warn "Contraseña del administrador inicial generada: ${ADMP}  (usuario: ver ADMIN_EMAIL en .env)"
  warn "Guárdala: podrás cambiarla luego. También puedes editar APP_PORT si 8090 está ocupado."
else
  log ".env ya existe; no se modifica."
fi

PORT="$(grep -E '^APP_PORT=' .env | cut -d= -f2)"; PORT="${PORT:-8090}"

# ------------------------------------------------------------
# 3) Construir y levantar (migraciones + seed admin automáticos)
# ------------------------------------------------------------
log "Construyendo y levantando contenedores..."
$DOCKER compose up -d --build

log "Esperando a que la aplicación responda..."
HEALTHY=0
for _ in $(seq 1 40); do
  if $DOCKER compose exec -T app python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)" >/dev/null 2>&1; then
    HEALTHY=1; break
  fi
  sleep 3
done
[ "$HEALTHY" = "1" ] || warn "La app tardó en responder. Revisa: $DOCKER compose logs -f app"

# ------------------------------------------------------------
# 4) Firewall: abrir el puerto de la app en la LAN (opcional)
# ------------------------------------------------------------
if command -v ufw >/dev/null 2>&1 && $SUDO ufw status | grep -q "Status: active"; then
  log "Abriendo el puerto ${PORT}/tcp en ufw..."
  $SUDO ufw allow "${PORT}/tcp" || true
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
log "¡Despliegue completo!"
echo "  Natillera: http://${IP:-localhost}:${PORT}"
echo "  Swagger:   http://${IP:-localhost}:${PORT}/api/v1/docs"
echo "  Admin:     ADMIN_EMAIL / ADMIN_PASSWORD de tu .env"
echo "  Cambia la contraseña del admin tras el primer ingreso."
