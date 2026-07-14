# Backend — Plataforma de Administración de Natilleras

Monolito modular (Clean Architecture + DDD). Ver `../docs` para el contexto de
negocio y `../CLAUDE.md` para los invariantes.

## Estado

**Sprint 0 (Fundaciones) — completo.** Esqueleto ejecutable con calidad de
producción: estructura de capas, shared domain (`Dinero`, `Periodo`,
`ReferenciaOrigen`), core (config, logging, errores, event bus, seguridad),
Unit of Work, repositorio con tenant, Auth JWT + RBAC, Docker y CI.

## Requisitos

- Python 3.12 (stack congelado). El entorno de desarrollo actual usa 3.11.9;
  el código es compatible con 3.11+ (ver nota en `pyproject.toml`).
- Docker (para MySQL y los tests financieros TEC-07). Opcional en local: sin
  Docker se usa SQLite para tests rápidos.

## Puesta en marcha (local, sin Docker)

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Comandos

```bash
# Arrancar la API (SQLite local por defecto)
uvicorn app.main:app --reload
# -> http://127.0.0.1:8000/health  y  /api/v1/docs

# Calidad (equivale al job de CI)
ruff check app tests          # estilo
mypy app                      # tipos estrictos
lint-imports                  # reglas de capas (TEC-03)
python scripts/guard_anti_float.py   # guarda anti-float (TEC-01)

# Tests
pytest -m "not mysql"         # rápidos (SQLite)
pytest -m mysql               # financieros (requieren MySQL, TEC-07)
```

## Con Docker (producción / integración)

```bash
cp ../.env.example ../.env    # y editar secretos
docker compose -f ../docker-compose.yml up --build
# El entrypoint espera MySQL, corre `alembic upgrade head` y arranca (Nginx :8080)
```

## Estructura

```
app/
  core/          config, logging, errors, eventbus, security, auth, deps
  shared/
    domain/      Dinero, Periodo, ReferenciaOrigen, base entidades/eventos
    application/ UnitOfWork (puerto), paginación
    infrastructure/ db, UoW SQLAlchemy, repositorio base con tenant
  modules/       natilleras, participantes, contabilidad, cuotas, prestamos,
                 actividades, multas, liquidacion  (cada uno con 4 capas)
tests/           unit, application, integration, api
alembic/         migraciones (001 en adelante, Sprint 1)
```

## Reglas de trabajo

Antes de implementar cualquier módulo, leer en orden: `../CLAUDE.md`,
`../docs/01-business-rules.md`, `../docs/02-domain-model.md`,
`../docs/05-backend-architecture.md` y el documento del módulo. Cada commit
referencia el `RF-xxx`/`RN-xxx` que implementa (doc 08).
