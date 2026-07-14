# 05 — Backend Architecture

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026-07-10 |
| Estado | Borrador — pendiente de aprobación |
| Stack | Python 3.12 · FastAPI 0.115.6 · SQLAlchemy 2.0.36 · Alembic 1.14.0 · Pydantic v2 · PyMySQL · PyJWT · structlog |
| Insumos | docs 01–04 |

---

## 1. Estilo arquitectónico

**Monolito modular con Clean Architecture y núcleo de dominio DDD.**

Justificación frente a alternativas:

- *Microservicios:* descartado para MVP. La consistencia transaccional del
  ledger (RNF-03) es trivial en un monolito y costosa distribuida. Los límites
  modulares del doc 02 permiten extraer servicios después si la escala lo
  exige.
- *CRUD en capas sin dominio:* descartado. Los invariantes financieros
  (INV-01..16) necesitan un lugar propio, testeable sin infraestructura.
- *Event sourcing completo:* descartado. El ledger append-only ya da la
  trazabilidad que el negocio necesita; event sourcing duplicaría el concepto
  con más complejidad. Nos quedamos con "ledger como fuente de verdad +
  eventos de dominio para coordinación".

## 2. Capas y regla de dependencias

```
┌────────────────────────────────────────────────────────┐
│ api/          FastAPI: routers, DTOs (schemas), deps    │  ← conoce app
├────────────────────────────────────────────────────────┤
│ application/  Casos de uso (services), UoW, event bus,  │  ← conoce domain
│               puertos (interfaces de repos)             │
├────────────────────────────────────────────────────────┤
│ domain/       Entidades, agregados, VOs, eventos,       │  ← no conoce a NADIE
│               excepciones, estrategias, matriz contable │
├────────────────────────────────────────────────────────┤
│ infrastructure/ SQLAlchemy models, repos concretos,     │  ← conoce domain y
│               mappers, UoW concreto, seguridad, logging │    application (implementa puertos)
└────────────────────────────────────────────────────────┘
```

Reglas duras (TEC-03):

- `domain/` es Python puro: sin imports de FastAPI, SQLAlchemy ni Pydantic.
- Los routers no contienen lógica: validan DTO → invocan caso de uso →
  mapean respuesta. Máximo ~15 líneas por endpoint.
- `application/` define puertos (`Protocol`); `infrastructure/` los
  implementa. La inyección se hace con el sistema de dependencias de FastAPI.
- Los modelos SQLAlchemy NO son las entidades de dominio: hay mappers
  explícitos (el costo se paga solo en los agregados ricos: Contabilidad,
  Prestamo, Actividad, Liquidacion; entidades simples como Participante pueden
  usar mapeo directo documentado como excepción).

## 3. Estructura de paquetes

```
backend/
├── alembic/                      # migraciones (orden doc 04 §6)
├── app/
│   ├── main.py                   # factory de FastAPI, handlers, middleware
│   ├── core/                     # transversales
│   │   ├── config.py             # Settings + FeatureFlags (pydantic-settings)
│   │   ├── security.py           # JWT access+refresh, hashing
│   │   ├── logging.py            # structlog JSON + request_id
│   │   ├── errors.py             # jerarquía de errores + formato uniforme
│   │   └── eventbus.py           # bus síncrono en memoria (interfaz + impl)
│   ├── modules/
│   │   ├── natilleras/
│   │   │   ├── api/  application/  domain/  infrastructure/
│   │   ├── participantes/ …
│   │   ├── contabilidad/         # LEDGER: único módulo que escribe asientos
│   │   ├── cuotas/ …
│   │   ├── prestamos/ …
│   │   ├── actividades/ …
│   │   ├── multas/ …
│   │   └── liquidacion/ …
│   └── shared/
│       ├── domain/               # Dinero, Periodo, ReferenciaOrigen, base de
│       │                         #   entidades/eventos, excepciones base
│       ├── application/          # UnitOfWork (puerto), paginación, resultados
│       └── infrastructure/       # UoW SQLAlchemy, repo base con tenant,
│                                 #   session factory, outbox futuro
└── tests/                        # espejo de la estructura (ver §9)
```

Cada módulo replica internamente las 4 capas. Prohibido importar
`modules/x/domain` desde `modules/y/*`: la comunicación entre módulos pasa por
eventos o por la capa application del módulo dueño. `shared/domain` es la única
excepción (VOs comunes).

## 4. Patrones aplicados (qué, dónde y por qué)

| Patrón | Dónde | Justificación |
|---|---|---|
| Repository | Puerto en application, impl. en infrastructure | Testear casos de uso sin BD; el repo del ledger NO expone update/delete (RN-060) |
| Repo base con tenant | `shared/infrastructure` | Filtro `natillera_id` obligatorio e inevitable (TEC-02); constructor exige el tenant del contexto |
| Unit of Work | `shared` | RNF-03: todos los asientos de una operación en una transacción; publica eventos al hacer commit |
| Domain Events + bus síncrono | `core/eventbus` | Traspasos a Rentabilidad desacoplados (doc 02 §6) dentro de la MISMA transacción; la interfaz permite migrar a outbox/async sin tocar dominio |
| Value Objects | `shared/domain` y por módulo | `Dinero` prohíbe float en construcción (TEC-01); validación en el borde del dominio |
| Factory | `Actividad.clonar_para`, creación de Natillera con sus 2 fondos | Construcciones con invariantes (RN-001, RN-049) |
| Strategy | `liquidacion/domain/estrategias` | Distribución configurable (RN-073) sin tocar el proceso |
| Specification | Consultas de elegibilidad (préstamo aprobable, número activo) | Reglas de selección reutilizables en dominio y queries |
| State machine explícita | `Natillera`, `Prestamo`, `Actividad`, `Multa`, `Liquidacion` | Transiciones válidas como datos + método `puede()` (RN-080/081) |
| CQRS ligero | Proyecciones de lectura (cuenta corriente, dashboard, reportes) como queries directas optimizadas, separadas de los casos de uso de escritura | Lecturas rápidas sin cargar agregados; NO se introduce MediatR-like: los casos de uso son clases invocables simples |
| DTO | Pydantic schemas solo en `api/` | El dominio no depende de Pydantic |

Decisión explícita sobre MediatR (brief): en Python no aporta; su rol lo cubren
casos de uso invocables + event bus. Queda registrado para no reabrirlo.

## 5. Ciclo de una operación financiera (ejemplo: pago de préstamo, RF-404)

```
POST /api/v1/prestamos/{uuid}/pagos
 → deps: auth JWT → usuario → rol (ADM|SUP) → tenant activo → estado natillera permite operación
 → router: valida DTO PagoPrestamoRequest
 → caso de uso RegistrarPagoPrestamo(uow, reloj, bus):
     1. abre UoW
     2. carga agregado Prestamo (repo con tenant)
     3. prestamo.registrar_pago(Dinero(...)) → descompone capital/interés,
        valida estado, emite PagoPrestamoRegistrado
     4. handler contable (módulo contabilidad) recibe el evento:
        Fondo.validar_asiento(...) × 2 → repo ledger .append() × 2
        + actualiza caches de saldo
     5. uow.commit()  # todo o nada (RNF-03)
 → respuesta DTO con los dos asientos generados (uuid, concepto, monto)
```

Si `validar_asiento` lanza `ViolacionSeparacionDeFondos`, el UoW hace rollback
completo: no existe estado intermedio posible.

## 6. Seguridad

- **AuthN:** JWT access (15 min) + refresh (14 días) con rotación y
  revocación (tabla `refresh_tokens`). Passlib+bcrypt para credenciales.
- **AuthZ (RBAC):** dependencia `require_rol(*roles)` por endpoint según la
  matriz del doc 03. El rol vive en `usuarios_natilleras`: un usuario puede
  ser ADM de una natillera y CLI de otra; el token porta usuario, y el tenant
  activo viaja en la ruta (`/natilleras/{uuid}/...`) validándose la membresía
  en cada request.
- **Tenancy:** el `natillera_id` resuelto por la dependencia es el ÚNICO que
  llega a los repos; nunca se acepta del body. CLI además restringe a su
  `participante_id` vinculado (RF-203).
- Rate limiting básico en login; bloqueo por intentos; headers de seguridad en
  Nginx.

## 7. Manejo de errores (formato uniforme, TEC-08)

Jerarquía: `ErrorDeDominio` (409/422 según tipo: `ViolacionSeparacionDeFondos`,
`TransicionInvalida`, `SaldoInsuficiente`, `TopePrestamosExcedido`...),
`NoEncontrado` (404), `NoAutorizado` (401), `Prohibido` (403),
`ErrorDeValidacion` (422, desde Pydantic).

Respuesta única:

```json
{
  "error": {
    "codigo": "SALDO_INSUFICIENTE",
    "mensaje": "El Fondo de Ahorro no tiene saldo suficiente para el desembolso",
    "detalle": {"saldo_disponible": "1250000.00", "monto_solicitado": "2000000.00"},
    "request_id": "..."
  }
}
```

Los códigos son un catálogo cerrado documentado en el doc 07 (API Design); el
frontend traduce código → mensaje UX (doc 06).

## 8. Observabilidad

- structlog JSON: `request_id` (middleware), `usuario_id`, `natillera_id`,
  `caso_de_uso`, latencia. Toda mutación loguea el resultado (asientos
  creados) — complementa, no sustituye, la auditoría en BD.
- `/health` (liveness) y `/ready` (BD + migraciones al día).
- Métrica interna clave: resultado del job de reconciliación (RF-802) — es el
  indicador de salud número uno del producto.

## 9. Estrategia de testing (la parte innegociable)

| Nivel | Alcance | Infra | Cobertura objetivo |
|---|---|---|---|
| Unit de dominio | Invariantes INV-01..16, VOs, máquinas de estado, estrategias, matriz contable EXHAUSTIVA (todo concepto × todo fondo × ambas naturalezas) | Ninguna (dominio puro) | 100% del dominio contable |
| Unit de aplicación | Casos de uso con repos fake en memoria | Ninguna | Flujos y errores principales |
| Integración financiera | Ledger, triggers de inmutabilidad, CHECKs, UoW, reconciliación, liquidación end-to-end con redondeos | **MySQL real en Docker** (TEC-07) | Todos los flujos que escriben asientos |
| API | Endpoints, RBAC, tenancy (RNF-02: test que intenta cruzar tenants en cada recurso), formato de error | SQLite en memoria (rápidos) | Contratos del doc 07 |
| Propiedad (hypothesis) | `Dinero`, descomposición capital/interés, distribución (suma == fondo para cualquier combinación) | Ninguna | Los 3 algoritmos monetarios |

Regla del CLAUDE.md operacionalizada: cada INV tiene al menos un test nombrado
`test_inv_XX_...`; un refactor que los rompa está mal por definición.

## 10. Configuración y feature flags (TEC-06)

- `Settings` (pydantic-settings) desde variables de entorno; sin secretos en
  el repositorio (`.env` solo local y en `.gitignore` — lección aprendida).
- `FeatureFlags` de sistema (por despliegue) + flags por natillera (tabla
  `feature_flags`, doc 04). La verificación es una dependencia/servicio
  `flags.exige('DONACIONES')` que lanza `FuncionalidadNoDisponible` (409).

## 11. Infraestructura de despliegue

Docker Compose de 2 servicios (definición del stack aprobado):

- **mysql:** MySQL 8, volumen persistente, healthcheck.
- **app:** imagen multi-stage — stage 1 compila el frontend (Vite build),
  stage 2 instala backend; runtime con supervisord orquestando Uvicorn y
  Nginx (estáticos + reverse proxy `/api`). Entrypoint: espera BD →
  `alembic upgrade head` → arranque.
- Backups: dump diario del volumen MySQL (obligatorio antes de cualquier
  `alembic upgrade` en producción). Restauración probada, no solo respaldada.

## 12. Decisiones registradas (ADR resumido)

| # | Decisión | Alternativa descartada | Motivo |
|---|---|---|---|
| ADR-01 | Monolito modular | Microservicios | Transaccionalidad del ledger, tamaño de equipo |
| ADR-02 | Ledger + eventos síncronos | Event sourcing / colas | Trazabilidad suficiente, menor complejidad operativa |
| ADR-03 | Dominio separado de modelos ORM con mappers en agregados ricos | Active Record total | Invariantes testeables sin BD |
| ADR-04 | Casos de uso invocables + bus propio | Port de MediatR | Idiomático en Python, sin dependencia extra |
| ADR-05 | Tests financieros en MySQL real | Solo SQLite | SQLite no respeta DECIMAL ni los triggers/CHECKs del diseño |
| ADR-06 | UUID público + BIGINT interno | UUID como PK | Rendimiento de índices InnoDB, sin exponer secuencias |
