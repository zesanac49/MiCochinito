# 09 — Sprint Backlog

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026-07-10 |
| Estado | Borrador — pendiente de aprobación |
| Supuesto | Sprints de 2 semanas; equipo: 1 dev + Claude Code. Estimaciones en puntos (1/2/3/5/8). |
| Destino | Estas tareas se convertirán en issues de Linear (proyecto por fase, etiquetas por módulo). |

Formato de tarea: `Sxx-Tyy · Título · [puntos] · trazas`.
Toda tarea hereda el Definition of Done del doc 08 §3.

---

## Sprint 0 — Fundaciones (sin lógica de negocio)

Objetivo: esqueleto ejecutable con calidad de producción desde el día uno.

- S0-T01 · Estructura de paquetes según doc 05 §3 + import-linter con las reglas de dependencia · [3] · TEC-03
- S0-T02 · Docker Compose (MySQL 8 + app multi-stage, supervisord, entrypoint con Alembic) · [5] · doc 05 §11
- S0-T03 · Settings + FeatureFlags (pydantic-settings), logging structlog con request_id, formato de error + handlers globales · [3] · TEC-06/08
- S0-T04 · Shared domain: `Dinero` (Decimal, prohíbe float), `Periodo`, `ReferenciaOrigen`, base de entidades y eventos + tests de propiedad de `Dinero` · [5] · TEC-01/04
- S0-T05 · UoW SQLAlchemy + bus de eventos síncrono + repo base con tenant obligatorio · [5] · TEC-02, RNF-03
- S0-T06 · Pipeline CI: ruff, mypy, tests SQLite + job de tests MySQL (Docker), grep de guardia anti-float · [3] · TEC-07, doc 08 §3
- S0-T07 · Auth JWT access+refresh con rotación y revocación + `require_rol` + tests · [5] · RF-1001

**Total S0: 29 pts** · Criterio de salida: `docker compose up` sirve `/health`, CI verde.

## Sprint 1 — Tenant y ledger (Fase 1a)

Objetivo: el núcleo contable existe y es inviolable antes que cualquier módulo.

- S1-T01 · Migración 001 (doc 04 §6) incluidos triggers de inmutabilidad · [5] · RN-060
- S1-T02 · Módulo natilleras: agregado + máquina de estados + matriz RN-081 (`puede()`) + endpoints RF-101/103 · [5] · RN-080/081
- S1-T03 · Configuración de natillera + historial con snapshots + RF-102 · [3] · RN-020
- S1-T04 · Módulo contabilidad: `Asiento`, `Fondo.validar_asiento` con matriz de conceptos + **tests exhaustivos concepto×fondo×naturaleza** · [8] · INV-01..03
- S1-T05 · Repositorio del ledger append-only + proyección CuentaCorriente + endpoint de asientos · [5] · RN-060/063, RF-803
- S1-T06 · Membresías usuario-natillera + RBAC por tenant + tests de aislamiento RNF-02 · [5] · RF-1002
- S1-T07 · Tests de integración MySQL: triggers rechazan UPDATE/DELETE; CHECKs rechazan conceptos inválidos · [3] · doc 04 §4

**Total S1: 34 pts** · Criterio de salida: imposible escribir un asiento inválido por ninguna vía; demo de transiciones de estado.

## Sprint 2 — Participantes y ahorro (Fase 1b)

- S2-T01 · Módulo participantes: alta, edición, estados, unicidad de documento · [3] · RF-201/202
- S2-T02 · Períodos del ciclo + generación al abrir la natillera · [3] · doc 04 §3.4
- S2-T03 · Cuotas: pago individual con idempotencia (constraint + Idempotency-Key) · [5] · RF-301
- S2-T04 · Pagos en lote con resumen de control · [3] · RF-302
- S2-T05 · Aportes extraordinarios (condicionados a configuración) · [2] · RF-303
- S2-T06 · Reversión de asientos con motivo · [3] · RF-305, RN-061
- S2-T07 · Estado de cuenta del participante (proyección + endpoint + saldos por concepto) · [5] · RF-203
- S2-T08 · Job de reconciliación + bloqueo preventivo de egresos ante descuadre · [5] · RF-802
- S2-T09 · Frontend: layout base neomórfico (tokens doc 06 §3), auth, selector de natillera · [5] · DIS-01..09
- S2-T10 · Frontend: participantes + registro de pagos en lote mobile-first (≤3 interacciones) · [5] · RNF-04/06

**Total S2: 39 pts** · Criterio de salida: una natillera real puede operar su ahorro completo.

## Sprint 3 — Préstamos y multas (Fase 2)

- S3-T01 · Agregado Prestamo: solicitud, aprobación con validaciones de topes y saldo, rechazo · [5] · RF-401/402, RN-037/038
- S3-T02 · Desembolso con revalidación de saldo (débito Ahorro) · [3] · RF-403
- S3-T03 · Pago con descomposición capital/interés → 2 asientos + tests de propiedad de la descomposición · [8] · RF-404, RN-033..035
- S3-T04 · Detección de mora (job) + transición EnMora ↔ EnPago · [3] · RF-405
- S3-T05 · Catálogo de multas + imposición manual y automática · [3] · RF-601, RF-304
- S3-T06 · Pago y anulación de multas · [3] · RF-602/603
- S3-T07 · Frontend: préstamos (lista, detalle con plan, flujos de aprobación/desembolso/pago) · [5] · RF-406
- S3-T08 · Frontend: multas + vista de mora · [3] · —

**Total S3: 33 pts**

## Sprint 4 — Actividades y polla (Fase 3)

- S4-T01 · Agregado Actividad genérico: creación, movimientos, cálculo de utilidad · [5] · RF-501/504, RN-040/041
- S4-T02 · Asignación anual de números + pagos por período (números activos/inactivos) · [5] · RF-502/503, RN-045/046
- S4-T03 · Sorteo sobre activos + caso sin ganador + inmutabilidad del resultado · [5] · RF-505, RN-047/048
- S4-T04 · Cierre con traspaso a Rentabilidad + manejo de pérdida (RN-042a) · [5] · RF-506
- S4-T05 · Clonación (factory) con exclusiones + linaje · [5] · RF-507, RN-049
- S4-T06 · Frontend: actividades + grilla de números neomórfica (estados pagado/inactivo, doc 06 §4) + sorteo + clonación en un clic · [8] · RF-508
- S4-T07 · Vista Cliente: mis números, mis pagos, resultados · [3] · RF-508

**Total S4: 36 pts**

## Sprint 5 — Liquidación y reportes (Fase 4)

- S5-T01 · Estrategias de distribución (3) + tests de propiedad (suma == fondo, redondeo) · [5] · RN-073
- S5-T02 · Proceso de liquidación: pre-validaciones, bloqueos, decisiones auditadas · [5] · RF-701/702
- S5-T03 · Cálculo + revisión + confirmación con doble verificación + asientos de cierre · [8] · RF-703/704
- S5-T04 · Acta PDF + registro de entregas de efectivo · [5] · RF-705/706
- S5-T05 · Reportes (recaudo, cartera, rentabilidad por fuente, polla) + export xlsx/pdf · [5] · RF-901/902
- S5-T06 · Dashboard de natillera · [3] · RF-104
- S5-T07 · Frontend: wizard de liquidación + reportes + exports · [8] · doc 06 §6
- S5-T08 · Prueba de ciclo completo: natillera sintética de 12 meses, liquidación con cuadre exacto · [5] · métrica visión §7

**Total S5: 44 pts** (candidato a dividirse en 5a/5b)

## Sprint 6 — Endurecimiento (Fase 5 inicial)

- S6-T01 · Backups automatizados + restauración probada · [3] · doc 05 §11
- S6-T02 · Auditoría de acciones completa + consulta con filtros · [3] · RF-803
- S6-T03 · Rate limiting, headers de seguridad, revisión de dependencias · [3] · doc 05 §6
- S6-T04 · Pruebas de carga sobre ledger y reportes con datos sintéticos (100 natilleras × 30 participantes × 12 meses) · [5] · doc 04 §7
- S6-T05 · Piloto: onboarding manual de 5 natilleras reales + feedback estructurado · [5] · visión §7

**Total S6: 19 pts + buffer para hallazgos del piloto**

---

## Reglas de gestión del backlog

1. No se inicia un sprint con documentos insumo sin aprobar.
2. Las tareas de dominio contable (S1-T04, S3-T03, S5-T01/T03) exigen Plan
   Mode y revisión humana del plan (doc 08 §2).
3. Cambios de alcance → nueva versión del documento afectado ANTES de la
   tarea, nunca después.
4. El burn-down se mide por RF completados (con DoD), no por tareas tocadas.
