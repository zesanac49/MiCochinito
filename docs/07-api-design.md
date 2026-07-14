# 07 — API Design

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026-07-10 |
| Estado | Borrador — pendiente de aprobación |
| Insumos | docs 03 (RF), 04 (esquema), 05 (arquitectura) |

---

## 1. Convenciones generales

- **Base:** `/api/v1`. Versionado por prefijo de ruta; cambios incompatibles
  → `/api/v2` (política: v1 se mantiene mínimo un ciclo anual).
- **Recursos anidados bajo el tenant:** todo recurso de negocio cuelga de
  `/natilleras/{natillera_uuid}/...`. El tenant JAMÁS viaja en el body
  (doc 05 §6).
- **Identificadores:** siempre `uuid` públicos; nunca ids numéricos.
- **Formato:** JSON; montos como **string decimal** (`"1250000.00"`) en
  requests y responses — nunca number de JSON, para preservar TEC-01 extremo
  a extremo. Fechas ISO-8601 UTC.
- **Verbos:** POST para acciones de dominio con nombre explícito
  (`/cerrar`, `/sortear`, `/clonar`) en lugar de PATCH genéricos: la API habla
  el lenguaje ubicuo, no CRUD.
- **Paginación:** `?page=1&size=25` (max 100) → envelope
  `{"items": [...], "total": n, "page": 1, "size": 25}`. Orden con
  `?sort=campo,-otro`. Filtros documentados por endpoint.
- **Idempotencia:** los POST financieros aceptan header
  `Idempotency-Key` (uuid); reintento con la misma clave devuelve el
  resultado original (protege pagos en conectividad intermitente, RF-302).
- **Errores:** formato único del doc 05 §7. Catálogo cerrado en §4.

## 2. Autenticación

| Método y ruta | Descripción | RF |
|---|---|---|
| POST `/auth/login` | email+password → access (15 min) + refresh (14 d) | RF-1001 |
| POST `/auth/refresh` | rota refresh, emite nuevo par | RF-1001 |
| POST `/auth/logout` | revoca refresh | RF-1001 |
| GET `/auth/me` | usuario + membresías (natilleras y roles) | RF-1001 |

`Authorization: Bearer <access>`. El frontend selecciona la natillera activa
de las membresías y la usa en las rutas.

## 3. Endpoints por módulo

Notación de acceso: `[A]`dministrador, `[S]`upervisor, `[C]`liente.

### Natilleras

| Método y ruta | Acceso | RF |
|---|---|---|
| POST `/natilleras` | [A]* | RF-101 |
| GET `/natilleras` (las del usuario) · GET `/natilleras/{uuid}` | A,S,C | — |
| PUT `/natilleras/{uuid}/configuracion` · GET ídem | A / A,S | RF-102 |
| POST `/natilleras/{uuid}/transiciones` body `{"a": "ABIERTA"}` | A | RF-103 |
| GET `/natilleras/{uuid}/dashboard` | A,S | RF-104 |
| GET/PUT `/natilleras/{uuid}/catalogo-multas` | A | RF-102 |
| GET/POST/DELETE `/natilleras/{uuid}/usuarios` (membresías) | A | RF-1002 |

*Creación de natilleras: rol de plataforma (onboarding manual en MVP).

### Participantes

| Método y ruta | Acceso | RF |
|---|---|---|
| POST `/…/participantes` · GET (lista, filtros: estado, q) | A / A,S | RF-201 |
| GET `/…/participantes/{uuid}` | A,S,C(propio) | — |
| PUT `/…/participantes/{uuid}` (datos de contacto) | A | RF-201 |
| POST `/…/participantes/{uuid}/estado` | A | RF-202 |
| GET `/…/participantes/{uuid}/cuenta` (asientos paginados + saldos) | A,S,C(propio) | RF-203 |

### Cuotas

| Método y ruta | Acceso | RF |
|---|---|---|
| GET `/…/periodos` · GET `/…/periodos/{uuid}/cuotas` (estado por participante) | A,S | RF-301 |
| POST `/…/cuotas/pagos` `{participante, periodo}` (Idempotency-Key) | A,S | RF-301 |
| POST `/…/cuotas/pagos-lote` `[{participante, periodo}...]` → resumen de control | A,S | RF-302 |
| POST `/…/aportes-extraordinarios` | A,S | RF-303 |
| POST `/…/asientos/{uuid}/reversion` `{motivo}` | A,S | RF-305 |

### Préstamos

| Método y ruta | Acceso | RF |
|---|---|---|
| POST `/…/prestamos` (solicitud) · GET lista (filtros: estado, participante) | A / A,S,C(propios) | RF-401/406 |
| GET `/…/prestamos/{uuid}` (detalle + plan + componentes pagados) | A,S,C(propio) | RF-406 |
| POST `/…/prestamos/{uuid}/aprobacion` `{decision, motivo?}` | A | RF-402 |
| POST `/…/prestamos/{uuid}/desembolso` | A | RF-403 |
| POST `/…/prestamos/{uuid}/pagos` `{monto}` (Idempotency-Key) → 2 asientos | A,S | RF-404 |

### Actividades

| Método y ruta | Acceso | RF |
|---|---|---|
| POST `/…/actividades` · GET lista (filtros: tipo, periodo, estado) | A / A,S,C | RF-501/508 |
| GET `/…/actividades/{uuid}` (CLI: incluye solo sus números) | A,S,C | RF-508 |
| PUT `/…/actividades/{uuid}/numeros` (asignación anual) | A | RF-502 |
| POST `/…/actividades/{uuid}/numeros/pagos` `{participante, numeros[]}` | A,S | RF-503 |
| POST `/…/actividades/{uuid}/movimientos` `{tipo, concepto, valor}` | A | RF-504 |
| POST `/…/actividades/{uuid}/sorteo` `{numero_ganador, fuente}` | A | RF-505 |
| POST `/…/actividades/{uuid}/cierre` | A | RF-506 |
| POST `/…/actividades/{uuid}/clonacion` `{periodo_destino}` | A | RF-507 |

### Multas

| Método y ruta | Acceso | RF |
|---|---|---|
| POST `/…/multas` · GET lista (filtros: estado, participante) | A / A,S,C(propias) | RF-601 |
| POST `/…/multas/{uuid}/pago` (Idempotency-Key) | A,S | RF-602 |
| POST `/…/multas/{uuid}/anulacion` `{justificacion}` | A | RF-603 |

### Liquidación

| Método y ruta | Acceso | RF |
|---|---|---|
| POST `/…/liquidacion` (inicia; responde bloqueos) | A | RF-701 |
| GET `/…/liquidacion` (estado, bloqueos, detalle si calculada) | A,S | RF-701 |
| POST `/…/liquidacion/decisiones` `{bloqueo, decision}` | A | RF-702 |
| POST `/…/liquidacion/calculo` | A | RF-703 |
| POST `/…/liquidacion/confirmacion` `{nombre_natillera}` (doble verificación) | A | RF-704 |
| GET `/…/liquidacion/acta` (PDF) | A,S | RF-705 |
| POST `/…/liquidacion/entregas` `{participante}` | A,S | RF-706 |

### Contabilidad, reportes y auditoría

| Método y ruta | Acceso | RF |
|---|---|---|
| GET `/…/fondos` (saldos + última reconciliación) | A,S | RF-104 |
| GET `/…/asientos` (filtros: fondo, concepto, participante, rango fechas) | A,S | RF-803 |
| GET `/…/reportes/{tipo}` tipo ∈ recaudo, cartera, rentabilidad-por-fuente, polla | A,S | RF-901 |
| GET `/…/reportes/{tipo}/export?formato=xlsx|pdf` · GET `/…/participantes/{uuid}/cuenta/export` | A,S,C(propio) | RF-902 |
| GET `/…/auditoria` (filtros: accion, usuario, entidad, fechas) | A | RF-803 |

## 4. Catálogo de códigos de error (cerrado)

| Código | HTTP | Cuándo |
|---|---|---|
| `NO_AUTENTICADO` / `TOKEN_EXPIRADO` | 401 | Auth |
| `PROHIBIDO` / `SIN_MEMBRESIA` | 403 | RBAC/tenancy |
| `NO_ENCONTRADO` | 404 | Recurso inexistente en el tenant |
| `VALIDACION` | 422 | DTO inválido (detalle por campo) |
| `TRANSICION_INVALIDA` | 409 | Máquinas de estado (RN-080/032/043/051) |
| `OPERACION_NO_PERMITIDA_EN_ESTADO` | 409 | Matriz RN-081 |
| `SALDO_INSUFICIENTE` | 409 | RN-007 (desembolso, pérdida de actividad) |
| `VIOLACION_SEPARACION_FONDOS` | 409 | Matriz contable (no debería alcanzarse desde la API; su presencia es alerta) |
| `TOPE_PRESTAMOS_EXCEDIDO` / `TOPE_CAPITAL_EXCEDIDO` | 409 | RN-037/038 |
| `PERIODO_YA_PAGADO` | 409 | Idempotencia RF-301 |
| `NUMERO_NO_DISPONIBLE` | 409 | RN-045 |
| `SORTEO_YA_REGISTRADO` | 409 | RF-505 |
| `ACTIVIDAD_NO_CERRABLE` | 409 | RN-042a (pérdida sin saldo) |
| `LIQUIDACION_BLOQUEADA` | 409 | RN-071 (incluye lista de bloqueos) |
| `CONFIRMACION_INCORRECTA` | 409 | RF-704 |
| `FUNCIONALIDAD_NO_DISPONIBLE` | 409 | Feature flag apagado (RN-091) |
| `CONFLICTO_IDEMPOTENCIA` | 409 | Misma clave, payload distinto |
| `ERROR_INTERNO` | 500 | Fallback (con request_id) |

## 5. Contratos de ejemplo (representativos)

**POST `/…/prestamos/{uuid}/pagos`** → `201`

```json
{
  "pago": {"uuid": "…", "fecha": "2026-07-10", "monto_recibido": "300000.00",
            "componente_capital": "250000.00", "componente_interes": "50000.00"},
  "asientos": [
    {"uuid": "…", "fondo": "AHORRO", "naturaleza": "CREDITO",
     "concepto": "RETORNO_CAPITAL", "monto": "250000.00"},
    {"uuid": "…", "fondo": "RENTABILIDAD", "naturaleza": "CREDITO",
     "concepto": "INTERES_PAGADO", "monto": "50000.00"}
  ],
  "prestamo": {"estado": "EN_PAGO", "saldo_capital": "750000.00"}
}
```

**POST `/…/liquidacion/calculo`** → `200`

```json
{
  "estado": "CALCULADA",
  "estrategia": "PROPORCIONAL_AHORRO",
  "fondo_rentabilidad": "4800000.00",
  "detalles": [
    {"participante": {"uuid": "…", "nombre": "…"},
     "ahorros": "1200000.00", "participacion_rentabilidad": "480000.00",
     "capital_pendiente": "0.00", "intereses_pendientes": "0.00",
     "multas_pendientes": "15000.00", "saldo_final": "1665000.00"}
  ],
  "control": {"suma_participaciones": "4800000.00", "cuadre": true}
}
```

## 6. Documentación viva

OpenAPI generado por FastAPI (`/api/v1/docs`) es la referencia ejecutable;
este documento define las convenciones y el contrato de negocio. Divergencia
entre ambos = defecto.
