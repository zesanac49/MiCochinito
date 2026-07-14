# Despliegue de Natillera en un servidor Linux (red local)

Natillera corre como **2 contenedores** (`mysql` + `app`), igual que “La Tienda”.
El servicio `app` sirve el **frontend (React)** y el **backend (FastAPI/uvicorn)**
detrás de **nginx**, aplica las **migraciones** al arrancar y siembra el
**administrador inicial**. El acceso es por la **red local**:

```
http://IP_DEL_SERVIDOR:8090
```

> Convive con la tienda sin chocar: la tienda usa el puerto **8080** y su propio
> MySQL; Natillera usa **8090** y un **MySQL propio aislado** (sin puerto al host).
> Si 8090 estuviera ocupado, cambia `APP_PORT` en el `.env`.

---

## Opción rápida (script todo-en-uno)

En el servidor, dentro de la carpeta del proyecto:

```bash
chmod +x server-setup.sh
./server-setup.sh
```

Instala Docker si falta, genera un `.env` con **secretos aleatorios** (incluida la
contraseña del admin, que se imprime al final), levanta los contenedores y abre el
puerto en el firewall. Al terminar muestra la URL y las credenciales.

---

## Paso a paso

### 1. Requisitos
- Servidor Linux (Ubuntu/Debian) en la red de la empresa, con `sudo`.
- 1 vCPU / 2 GB RAM mínimo (2 vCPU / 4 GB recomendado).

### 2. Instalar Docker + Compose
```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker
```

### 3. Obtener el código (git)
```bash
cd /opt
sudo git clone <URL_DE_TU_REPO> natillera
sudo chown -R $USER:$USER /opt/natillera
cd /opt/natillera
```

### 4. Configurar variables de entorno
```bash
cp .env.example .env
nano .env
```
Cambia **obligatoriamente**:
```dotenv
MYSQL_PASSWORD=...          # openssl rand -hex 16
MYSQL_ROOT_PASSWORD=...     # openssl rand -hex 16
JWT_SECRET=...              # openssl rand -hex 32
ADMIN_EMAIL=admin@tuempresa.com
ADMIN_PASSWORD=...          # la clave del primer ingreso
# APP_PORT=8090             # cámbialo solo si 8090 está ocupado
```
> `DATABASE_URL` NO se define aquí: `docker-compose` la compone con las
> credenciales de MySQL.

### 5. Levantar
```bash
docker compose up -d --build
# o:  ./deploy.sh
```
Esto construye las imágenes, arranca MySQL y `app`, **aplica migraciones** y
**crea el administrador** (todo en el entrypoint).

Sigue el arranque:
```bash
docker compose ps
docker compose logs -f app
```

### 6. Abrir el puerto en el firewall (si usas ufw)
```bash
sudo ufw allow 8090/tcp
```

### 7. Verificar
```bash
curl -f http://127.0.0.1:8090/health      # {"estado":"ok"} (o similar)
```
Desde otra máquina de la LAN: `http://IP_DEL_SERVIDOR:8090`

### 8. Primer ingreso
- Entra con `ADMIN_EMAIL` / `ADMIN_PASSWORD` del `.env`.
- Ve a **Natillera → Crear** para crear tu natillera: quedas como su **Administrador**.
- Desde **Usuarios** puedes dar acceso a más personas y asignarles rol.

---

## Operación y mantenimiento

**Logs / estado:**
```bash
docker compose logs -f app
docker compose ps
```

**Reiniciar / detener** (los datos de MySQL persisten en el volumen):
```bash
docker compose restart app
docker compose down
```

**Actualizar a una nueva versión:**
```bash
cd /opt/natillera
./update.sh          # git pull + rebuild (migraciones automáticas)
```

**Respaldo / restauración de la BD:**
```bash
./scripts/backup.sh backups
./scripts/restore.sh backups/natillera-YYYYMMDD-HHMMSS.sql
```
Respaldo diario (cron 2am):
```bash
crontab -e
# 0 2 * * * cd /opt/natillera && ./scripts/backup.sh backups >> backups/backup.log 2>&1
```

---

## Solución de problemas

| Síntoma | Revisa |
|---|---|
| `app` reinicia en bucle | `docker compose logs app` — suele ser BD no lista o `.env` mal |
| No abre desde otra PC | ¿Abriste `8090/tcp` en el firewall? ¿IP correcta? |
| `entrypoint` falla con `\r` | Los `.sh` deben ser **LF** (lo fuerza `.gitattributes`) |
| Puerto 8090 ocupado | Cambia `APP_PORT` en `.env` y `docker compose up -d` |
| Sin espacio | `docker system prune -f` |

> **Producción real / acceso externo:** este despliegue es para **red local sin
> HTTPS**. Si algún día se expone a internet, coloca un reverse proxy con TLS
> (Caddy o Nginx) delante de `127.0.0.1:8090`, como en el `DEPLOY.md` de la tienda.
