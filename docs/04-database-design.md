# 04 — Database Design

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026-07-10 |
| Estado | Borrador — pendiente de aprobación |
| Motor | MySQL 8 (InnoDB, utf8mb4) · SQLAlchemy 2.0 (Mapped) · Alembic |
| Insumos | `02-domain-model.md` v1.0 · `03-functional-requirements.md` v1.0 |

---

## 1. Convenciones globales

- **Nombres:** snake_case, español, plural para tablas (`participantes`),
  singular para columnas.
- **PK:** `id BIGINT UNSIGNED AUTO_INCREMENT` (interno) + `uuid CHAR(36)
  UNIQUE NOT NULL` (identificador público expuesto por la API; nunca se
  exponen ids autoincrementales).
- **Tenant (TEC-02):** toda tabla de negocio lleva `natillera_id BIGINT NOT
  NULL` con FK e índice. Excepciones: `natilleras` (es el tenant) y tablas
  globales del sistema (`usuarios` se asocia vía tabla puente).
- **Dinero (TEC-01):** `DECIMAL(15,2) NOT NULL`. Prohibido `FLOAT`/`DOUBLE`
  en cualquier columna monetaria. Tasas: `DECIMAL(7,4)`.
- **Tiempos:** `created_at`/`updated_at` `DATETIME(6)` UTC en todas las
  tablas; el ledger no tiene `updated_at` (es inmutable).
- **Enums:** `VARCHAR(30)` + `CHECK` (no `ENUM` nativo de MySQL, para que
  agregar valores sea migración de constraint y no reconstrucción de tabla).
- **Borrado:** lógico donde el negocio lo permita (`estado`), jamás físico en
  entidades con historia (RN-012); físico solo en tablas de configuración sin
  referencias.
- **FKs:** `ON DELETE RESTRICT` por defecto. Nada en cascada sobre datos
  financieros.

## 2. Diagrama de relaciones (visión general)

```
usuarios ──< usuarios_natilleras >── natilleras ──1─┬─ configuraciones (1:1)
                                                    ├─< participantes
                                                    ├─< fondos (exactamente 2)
                                                    ├─< asientos (LEDGER)
                                                    ├─< periodos
                                                    ├─< prestamos ──< prestamo_pagos
                                                    ├─< actividades ─┬─< actividad_numeros
                                                    │                ├─< actividad_movimientos
                                                    │                └─ 1 sorteo (0..1)
                                                    ├─< multas
                                                    └─ 1 liquidaciones ──< liquidacion_detalles
                                                                       └─< liquidacion_decisiones
asientos >── fondos · participantes(opc) · referencia polimórfica (origen_tipo + origen_id)
auditoria_acciones: acciones no contables (transiciones, anulaciones, decisiones)
```

## 3. Tablas por módulo

### 3.1 Gestión de natilleras

**`natilleras`** — id, uuid, nombre, `estado` CHECK
(`BORRADOR|ABIERTA|EN_OPERACION|PENDIENTE_LIQUIDACION|LIQUIDADA|ARCHIVADA`),
`ciclo_inicio DATE`, `ciclo_fin DATE`, timestamps. *(RN-080)*

**`configuraciones`** (1:1 con natillera) — valor_cuota DECIMAL(15,2),
periodicidad_cuota CHECK(`MENSUAL|QUINCENAL|SEMANAL`), dia_limite_pago
TINYINT, permite_aportes_extra BOOL, tasa_interes_base DECIMAL(7,4),
tasa_interes_min/max DECIMAL(7,4), max_prestamos_activos TINYINT DEFAULT 2,
max_capital_vigente DECIMAL(15,2), estrategia_distribucion CHECK
(`PARTES_IGUALES|PROPORCIONAL_AHORRO|PROPORCIONAL_TIEMPO`),
estrategia_congelada BOOL DEFAULT FALSE. *(RF-102; RN-020/021/031/037/038/073)*

Los cambios de configuración se versionan en **`configuraciones_historial`**
(snapshot JSON + autor + fecha) para poder auditar "qué regla regía cuándo".
*(RN-020)*

**`catalogo_multas`** — natillera_id, nombre, tipo CHECK
(`MORA_CUOTA|MORA_PRESTAMO|MORA_ACTIVIDAD|OTRA`), valor DECIMAL(15,2),
activo BOOL. *(RN-050)*

**`feature_flags`** — natillera_id, flag VARCHAR(50), habilitado BOOL. Flags
del MVP sembrados en `FALSE`: `DONACIONES`, `RENDIMIENTOS_BANCARIOS`, `CDT`,
`INVERSIONES`, `OTROS_INGRESOS`. *(RN-091, TEC-06)*

### 3.2 Usuarios y acceso

**`usuarios`** — id, uuid, email UNIQUE, hash_password, nombre, activo,
timestamps.

**`usuarios_natilleras`** — usuario_id, natillera_id, rol CHECK
(`ADMINISTRADOR|SUPERVISOR|CLIENTE`), participante_id NULL (obligatorio si
rol=CLIENTE; FK a participante de la MISMA natillera — validado por trigger y
por dominio), UNIQUE(usuario_id, natillera_id). *(RF-1002)*

**`refresh_tokens`** — usuario_id, token_hash, expira_en, revocado. *(RF-1001)*

### 3.3 Participantes

**`participantes`** — id, uuid, natillera_id, nombre, tipo_documento CHECK
(`CC|CE|TI|PP`), numero_documento, telefono, direccion, estado CHECK
(`ACTIVO|SUSPENDIDO|RETIRADO`), fecha_ingreso DATE, timestamps.
`UNIQUE(natillera_id, tipo_documento, numero_documento)`. *(RN-010/011/012)*

### 3.4 Contabilidad (núcleo)

**`fondos`** — id, uuid, natillera_id, tipo CHECK(`AHORRO|RENTABILIDAD`),
saldo_cache DECIMAL(15,2) DEFAULT 0, saldo_cache_actualizado DATETIME(6).
`UNIQUE(natillera_id, tipo)` — garantiza exactamente un fondo de cada tipo.
*(RN-001; RN-063: el cache es reconciliable, nunca fuente de verdad)*

**`periodos`** — natillera_id, anio SMALLINT, mes TINYINT, fecha_limite_cuota
DATE, conciliado BOOL. `UNIQUE(natillera_id, anio, mes)`. *(RF-304, RN-071)*

**`asientos`** — EL LEDGER. DDL completo por su criticidad:

```sql
CREATE TABLE asientos (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  uuid            CHAR(36)     NOT NULL UNIQUE,
  natillera_id    BIGINT       NOT NULL,
  fondo_id        BIGINT       NOT NULL,
  participante_id BIGINT       NULL,
  naturaleza      VARCHAR(10)  NOT NULL,  -- CHECK: DEBITO | CREDITO
  concepto        VARCHAR(40)  NOT NULL,  -- CHECK: matriz doc 02 §5
  monto           DECIMAL(15,2) NOT NULL, -- CHECK: monto > 0
  periodo_id      BIGINT       NULL,
  origen_tipo     VARCHAR(30)  NOT NULL,  -- CUOTA|PRESTAMO|PAGO_PRESTAMO|ACTIVIDAD|MULTA|LIQUIDACION|REVERSION
  origen_id       BIGINT       NOT NULL,
  reversa_de_id   BIGINT       NULL,      -- FK a asientos.id (RN-061)
  descripcion     VARCHAR(255) NOT NULL,
  creado_por      BIGINT       NOT NULL,  -- FK usuarios
  created_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  CONSTRAINT chk_naturaleza CHECK (naturaleza IN ('DEBITO','CREDITO')),
  CONSTRAINT chk_monto_positivo CHECK (monto > 0),
  CONSTRAINT chk_concepto CHECK (concepto IN (
    'CUOTA_AHORRO','APORTE_EXTRAORDINARIO','DESEMBOLSO_PRESTAMO',
    'RETORNO_CAPITAL','INTERES_PAGADO','UTILIDAD_ACTIVIDAD',
    'PERDIDA_ACTIVIDAD','MULTA_PAGADA','DEVOLUCION_AHORRO',
    'DISTRIBUCION_RENTABILIDAD','REVERSION'))
  -- FKs: natillera_id, fondo_id, participante_id, periodo_id,
  --      reversa_de_id, creado_por (todas RESTRICT)
);

-- Inmutabilidad a nivel de motor (defensa en profundidad de RN-060):
CREATE TRIGGER trg_asientos_no_update BEFORE UPDATE ON asientos
  FOR EACH ROW SIGNAL SQLSTATE '45000'
  SET MESSAGE_TEXT = 'LEDGER INMUTABLE: UPDATE prohibido (RN-060)';
CREATE TRIGGER trg_asientos_no_delete BEFORE DELETE ON asientos
  FOR EACH ROW SIGNAL SQLSTATE '45000'
  SET MESSAGE_TEXT = 'LEDGER INMUTABLE: DELETE prohibido (RN-060)';
```

Índices del ledger: `(natillera_id, fondo_id, created_at)`,
`(natillera_id, participante_id, created_at)`,
`(natillera_id, concepto)`, `(origen_tipo, origen_id)`.

Nota: la validación concepto↔fondo (matriz doc 02 §5) vive en el dominio
(`Fondo.validar_asiento`) con tests exhaustivos; el CHECK de concepto en BD es
una segunda línea. Un trigger adicional que valide la combinación
concepto+tipo_de_fondo se añadirá en la migración del módulo Contabilidad como
tercera línea (defensa en profundidad para un producto financiero).

### 3.5 Cuotas

**`cuotas`** — natillera_id, participante_id, periodo_id, valor
DECIMAL(15,2), estado CHECK(`PENDIENTE|PAGADA|REVERTIDA`), pagada_en
DATETIME(6) NULL, asiento_id NULL (FK al asiento que la pagó).
`UNIQUE(natillera_id, participante_id, periodo_id)` — la idempotencia de
RF-301 como constraint. *(RN-002, RF-301)*

### 3.6 Préstamos

**`prestamos`** — id, uuid, natillera_id, participante_id, capital
DECIMAL(15,2), tasa_interes DECIMAL(7,4), plazo_meses TINYINT,
fecha_desembolso DATE NULL, estado CHECK
(`SOLICITADO|APROBADO|RECHAZADO|DESEMBOLSADO|EN_PAGO|EN_MORA|PAGADO`),
motivo_rechazo VARCHAR(255) NULL, saldo_capital DECIMAL(15,2) (cache
reconciliable), timestamps. Índice `(natillera_id, participante_id, estado)`
— soporta RN-037/038. *(RN-030..038)*

**`prestamo_pagos`** — prestamo_id, natillera_id, fecha, monto_recibido
DECIMAL(15,2), componente_capital DECIMAL(15,2), componente_interes
DECIMAL(15,2), asiento_capital_id FK, asiento_interes_id FK.
`CHECK (componente_capital + componente_interes = monto_recibido)`.
*(RN-033: la descomposición y sus dos asientos quedan enlazados)*

### 3.7 Actividades

**`actividades`** — id, uuid, natillera_id, tipo CHECK
(`POLLA|RIFA|BINGO|BAZAR|VENTA|OTRO|DONACION`), nombre, periodo_id, estado
CHECK(`BORRADOR|ABIERTA|SORTEADA|CERRADA`), valor_numero DECIMAL(15,2) NULL,
cantidad_numeros SMALLINT NULL, premio DECIMAL(15,2) NULL, fecha_sorteo DATE
NULL, clonada_de_id NULL (FK a actividades — linaje de clonación, RF-507),
utilidad_cierre DECIMAL(15,2) NULL (sellada al cerrar), timestamps.
*(RN-040/043/044/049; `DONACION` presente en el CHECK pero bloqueada por flag)*

**`actividad_numeros`** — actividad_id, natillera_id, numero SMALLINT,
participante_id, pagado BOOL DEFAULT FALSE, pagado_en DATETIME(6) NULL.
`UNIQUE(actividad_id, numero)`. Índice `(actividad_id, pagado)` — el sorteo
consulta solo activos. *(RN-045/046/047)*

**`actividad_movimientos`** — actividad_id, natillera_id, tipo CHECK
(`INGRESO|GASTO|PREMIO`), concepto VARCHAR(120), valor DECIMAL(15,2),
participante_id NULL (p. ej. quién pagó números). La utilidad se calcula de
esta tabla; no es editable. *(RN-041, RF-504)*

**`sorteos`** — actividad_id UNIQUE, numero_ganador SMALLINT, hubo_ganador
BOOL, participante_ganador_id NULL, fuente VARCHAR(120) (lotería de
referencia), registrado_por, created_at. Inmutable por trigger (mismo patrón
del ledger). *(RN-047/048, RF-505)*

### 3.8 Multas

**`multas`** — id, uuid, natillera_id, participante_id, catalogo_multa_id,
valor DECIMAL(15,2), motivo VARCHAR(255), origen_tipo/origen_id (qué la
causó), estado CHECK(`IMPUESTA|PAGADA|ANULADA`), pagada_en NULL,
asiento_id NULL, anulada_por NULL, justificacion_anulacion VARCHAR(255) NULL,
timestamps. *(RN-050/051/052)*

### 3.9 Liquidación

**`liquidaciones`** — id, uuid, natillera_id UNIQUE (una por ciclo en MVP),
estado CHECK(`PRE_VALIDACION|CALCULADA|EN_REVISION|CONFIRMADA|ACTA_GENERADA`),
estrategia_aplicada VARCHAR(30), saldo_rentabilidad_distribuido
DECIMAL(15,2), confirmada_por NULL, confirmada_en NULL, timestamps.
*(RN-070/073/074)*

**`liquidacion_detalles`** — liquidacion_id, natillera_id, participante_id,
ahorros DECIMAL(15,2), participacion_rentabilidad DECIMAL(15,2),
capital_pendiente DECIMAL(15,2), intereses_pendientes DECIMAL(15,2),
multas_pendientes DECIMAL(15,2), saldo_final DECIMAL(15,2),
entregado BOOL DEFAULT FALSE, entregado_en NULL, entregado_por NULL.
`CHECK (saldo_final = ahorros + participacion_rentabilidad - capital_pendiente
- intereses_pendientes - multas_pendientes)`. *(RN-072, RF-704/706)*

**`liquidacion_decisiones`** — liquidacion_id, tipo_bloqueo, referencia
(origen_tipo/origen_id), decision VARCHAR(255), decidido_por, created_at.
*(RN-071, RF-702)*

### 3.10 Auditoría de acciones

**`auditoria_acciones`** — natillera_id, usuario_id, accion VARCHAR(60)
(TRANSICION_ESTADO, ANULACION_MULTA, DECISION_LIQUIDACION, CAMBIO_CONFIG,
SORTEO, CLONACION, REVERSION...), entidad_tipo, entidad_id, detalle JSON,
created_at. Append-only (mismos triggers del ledger). Complementa al ledger:
el ledger audita dinero; esta tabla audita decisiones. *(RN-062, INV-13)*

## 4. Integridad de la separación de fondos — defensa en 3 capas

| Capa | Mecanismo | Falla que detiene |
|---|---|---|
| 1. Dominio | `Fondo.validar_asiento` + matriz de conceptos (tests exhaustivos) | Bug de lógica en services |
| 2. Constraint | CHECKs de concepto/naturaleza/monto en `asientos` | Bypass del dominio (script, fixture, SQL manual) |
| 3. Trigger | Inmutabilidad UPDATE/DELETE + validación concepto↔fondo | Acceso directo a BD, migración errónea |

## 5. Estrategia de saldos y reconciliación

- Fuente de verdad: `SUM(asientos)` por fondo/participante/concepto.
- `fondos.saldo_cache` y `prestamos.saldo_capital` son cachés que el Unit of
  Work actualiza en la misma transacción del asiento.
- **Job de reconciliación (RF-802):** recalcula desde el ledger y compara.
  Discrepancia → registro en `auditoria_acciones` + alerta + bloqueo de
  egresos del tenant afectado.

## 6. Migraciones (Alembic)

- **Migración 001:** natilleras, configuraciones, usuarios,
  usuarios_natilleras, participantes, fondos, periodos, asientos (+ triggers),
  auditoria_acciones, feature_flags. El tenant y el ledger nacen primero
  (TEC-02, TEC-09).
- Orden posterior por fases del roadmap: 002 cuotas/catálogo multas/multas,
  003 préstamos, 004 actividades/sorteos, 005 liquidación.
- Reglas: ninguna migración ejecuta UPDATE/DELETE sobre `asientos`,
  `sorteos` ni `auditoria_acciones`; los triggers se recrean explícitamente si
  una migración toca esas tablas; toda migración es reversible
  (`downgrade`) salvo las que solo agregan valores a CHECKs.
- Aplicación: en el entrypoint del contenedor (según infraestructura definida).

## 7. Consideraciones de rendimiento (escala: miles de natilleras)

- Todos los índices comienzan por `natillera_id` (partición lógica por
  tenant; particionamiento físico se evalúa post-MVP con datos reales).
- El ledger crece sin límite: índices cubrientes para las proyecciones de
  cuenta corriente y reportes por fuente; archivado a tablas históricas solo
  para natilleras `Archivada` (proceso post-MVP).
- Lecturas de dashboard sirven del caché reconciliable, no de agregaciones en
  caliente.
- Pool de conexiones dimensionado en doc 05; consultas de reportes con
  `read-only` transaction.

## 8. Datos semilla

- Flags del sistema en FALSE (§3.1).
- Catálogo de multas de ejemplo por natillera nueva (editable).
- Usuario administrador inicial por proceso de onboarding manual (Fase 5 lo
  automatiza).
