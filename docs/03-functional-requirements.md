# 03 — Functional Requirements

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026-07-10 |
| Estado | Borrador — pendiente de aprobación |
| Insumos | `01-business-rules.md` v1.1 · `02-domain-model.md` v1.0 |

Convenciones:

- **RF-xxx** — requisito funcional. Numeración por módulo (centenas).
- **Actor:** `ADM` (Administrador), `SUP` (Supervisor), `CLI` (Cliente/participante), `SYS` (sistema).
- **Trazas:** reglas RN-xxx que el requisito implementa o respeta.
- Todo RF hereda implícitamente: filtro de tenant (TEC-02), verificación de
  estado de natillera (RN-081), registro de auditoría (RN-062) y RBAC.
- Prioridad: `M` (Must, MVP), `S` (Should, MVP si el cronograma lo permite),
  `F` (Futuro, fuera del MVP).

Matriz de permisos base (refinada por RF):

| Capacidad | ADM | SUP | CLI |
|---|---|---|---|
| Configurar natillera, transiciones de estado | ✔ | ✗ | ✗ |
| Registrar pagos (cuotas, préstamos, actividades, multas) | ✔ | ✔ | ✗ |
| Crear/aprobar préstamos, imponer/anular multas, sortear, cerrar, liquidar | ✔ | ✗ | ✗ |
| Consultar información propia | ✔ | ✔ | ✔ (solo la propia) |
| Consultar información de todos | ✔ | ✔ | ✗ |

---

## 100 — Gestión de natilleras

**RF-101 (M, ADM) — Crear natillera.** Crea una natillera en estado `Borrador`
con su configuración inicial y sus dos fondos en cero. Criterios: no admite
movimientos financieros en `Borrador`; los fondos no pueden crearse ni
eliminarse por separado. *(RN-001, RN-080, RN-081)*

**RF-102 (M, ADM) — Configurar natillera.** Edita: cuota (valor/periodicidad),
aportes extraordinarios on/off, tasa base y límites, tope de préstamos
concurrentes, monto máximo de capital vigente, catálogo de multas, estrategia
de distribución. Criterios: cambios rigen hacia futuro; nunca recalculan
hechos pasados; estrategia bloqueada desde `PendienteLiquidacion`.
*(RN-020, RN-021, RN-031, RN-037, RN-038, RN-050, RN-073)*

**RF-103 (M, ADM) — Transicionar estado.** Avanza la máquina de estados con
confirmación explícita. Criterios: solo transiciones válidas en orden; cada
transición valida requisitos de entrada (p. ej. a `PendienteLiquidacion` exige
configuración completa) y queda auditada. *(RN-080, RN-081)*

**RF-104 (S, ADM) — Dashboard de natillera.** Muestra: saldo de cada fondo
(derivado del ledger), cartera de préstamos, mora, actividades del período,
multas pendientes. Criterios: los saldos provienen de la proyección contable;
prohibido calcularlos en frontend. *(RN-063)*

## 200 — Participantes

**RF-201 (M, ADM) — Inscribir participante.** Alta con nombre, documento,
teléfono, dirección. Criterios: documento único en la natillera; estado
inicial `Activo`; fecha de ingreso registrada (insumo de distribución
ponderada). *(RN-010, RN-011)*

**RF-202 (M, ADM) — Cambiar estado del participante.** `Activo ↔ Suspendido`,
`→ Retirado`. Criterios: `Retirado` conserva historial y cuenta; nunca hay
borrado físico; retiro con saldos pendientes exige decisión auditada.
*(RN-012)*

**RF-203 (M, ADM/SUP/CLI) — Consultar estado de cuenta.** Muestra la cuenta
corriente: asientos con fecha, concepto, débito/crédito, referencia de origen,
y saldos por concepto (ahorros, capital adeudado, intereses pendientes, multas
pendientes). CLI solo ve la propia. Criterios: la vista es proyección del
ledger; exportable (RF-902). *(RN-013, RN-060..063)*

## 300 — Cuotas y aportes

**RF-301 (M, ADM/SUP) — Registrar pago de cuota.** Registra el pago en
efectivo de la cuota del período. Criterios: genera crédito `CUOTA_AHORRO` al
Fondo de Ahorro; idempotencia por (participante, período): un período pagado
no admite doble registro sin reversión previa. *(RN-002, RN-020, RN-060)*

**RF-302 (M, ADM/SUP) — Registro de pagos en lote.** Pantalla operativa
mobile-first para registrar los pagos del día de múltiples participantes en
una sola sesión. Criterios: cada pago genera su asiento individual; resumen de
control (total recaudado) al confirmar. *(RN-002; visión §8 — conectividad)*

**RF-303 (M, ADM/SUP) — Registrar aporte extraordinario.** Solo si está
habilitado en configuración. Crédito `APORTE_EXTRAORDINARIO` al Ahorro.
*(RN-021)*

**RF-304 (M, SYS) — Detectar mora en cuotas.** Al vencer la fecha límite del
período sin pago, impone automáticamente la multa configurada (si existe en el
catálogo). Criterios: la multa nace `Impuesta`; no toca ningún fondo hasta su
pago. *(RN-022, RN-050, RN-052)*

**RF-305 (M, ADM/SUP) — Revertir un pago erróneo.** Genera asiento de
reversión referenciando el original más el asiento correcto si aplica.
Criterios: prohibido editar o eliminar el asiento original; motivo
obligatorio. *(RN-061)*

## 400 — Préstamos

**RF-401 (M, ADM) — Registrar solicitud de préstamo.** Capital, plazo, tasa
(dentro de límites configurados). Estado `Solicitado`. *(RN-031)*

**RF-402 (M, ADM) — Aprobar o rechazar solicitud.** Criterios de aprobación
validados por el dominio: saldo suficiente del Fondo de Ahorro, tope de
préstamos concurrentes, tope de capital vigente del participante. El rechazo
registra motivo. *(RN-007, RN-030, RN-037, RN-038)*

**RF-403 (M, ADM) — Desembolsar préstamo.** Genera débito
`DESEMBOLSO_PRESTAMO` al Fondo de Ahorro; estado → `Desembolsado`/`EnPago`.
Criterios: revalida saldo al momento de confirmar (no al aprobar). *(RN-003, RN-007, RN-030)*

**RF-404 (M, ADM/SUP) — Registrar pago de préstamo.** Recibe un monto y el
dominio lo descompone en capital e interés según el plan. Criterios: genera
dos asientos separados — `RETORNO_CAPITAL` (crédito Ahorro) e
`INTERES_PAGADO` (crédito Rentabilidad); jamás un asiento combinado; el
interés causado no pagado permanece como cuenta por cobrar. *(RN-033, RN-034, RN-035)*

**RF-405 (M, SYS) — Detectar mora en préstamos.** Cuota de préstamo vencida →
estado `EnMora` + multa del catálogo. Al ponerse al día retorna a `EnPago`.
*(RN-032, RN-036)*

**RF-406 (M, ADM/SUP/CLI) — Consultar préstamos.** Lista y detalle con plan de
pagos, pagado/pendiente por componente. CLI solo los propios. *(RN-013)*

## 500 — Actividades y polla

**RF-501 (M, ADM) — Crear actividad.** Tipo, período, configuración (para
polla: valor por número, cantidad de números, premio, fecha de sorteo). Estado
`Borrador`. *(RN-040, RN-044)*

**RF-502 (M, ADM) — Asignar números de polla.** Asigna `NumeroPolla` a
participantes; un participante puede tener varios. Criterios: los números son
únicos dentro de la polla; la asignación es anual: se hace una vez y las
clonaciones la heredan. *(RN-045)*

**RF-503 (M, ADM/SUP) — Registrar pago de números del período.** Marca pagados
los números de un participante para el período. Criterios: genera ingreso de
la actividad; un número sin pago queda `Inactivo` para el sorteo del período.
*(RN-046)*

**RF-504 (M, ADM) — Registrar ingresos, gastos y premios.** Para cualquier
tipo de actividad. Criterios: afectan solo el cálculo de utilidad de la
actividad; ningún asiento a fondos hasta el cierre. *(RN-041, RN-043)*

**RF-505 (M, ADM) — Ejecutar sorteo de polla.** Registra el número ganador del
mecanismo externo (lotería). Criterios: el sistema evalúa solo números
activos; si el ganador no está activo → `SorteoSinGanador` y la utilidad
íntegra irá a Rentabilidad al cierre; resultado inmutable una vez registrado.
*(RN-047, RN-048)*

**RF-506 (M, ADM) — Cerrar actividad.** Calcula utilidad y la traslada a
Rentabilidad. Criterios: utilidad = ingresos − premios − gastos, no editable;
si es negativa, valida saldo de Rentabilidad y genera débito
`PERDIDA_ACTIVIDAD` (bloquea si el saldo es insuficiente); estado → `Cerrada`
irreversible. *(RN-041, RN-042, RN-042a, RN-043)*

**RF-507 (M, ADM) — Clonar actividad del período anterior.** Criterios: copia
participantes, números, configuración, premio y valor; excluye pagos, ganador,
sorteo, evidencias y auditoría; nace en `Borrador`; operación completa en
< 1 minuto (métrica de visión §7). *(RN-049)*

**RF-508 (S, ADM/SUP/CLI) — Consultar actividad.** Estado, números propios
(CLI), pagos, utilidad proyectada (ADM/SUP). *(RN-013)*

## 600 — Multas

**RF-601 (M, ADM) — Imponer multa manual.** Tipo del catálogo, participante,
motivo. Estado `Impuesta`. *(RN-050, RN-051)*

**RF-602 (M, ADM/SUP) — Registrar pago de multa.** Estado → `Pagada`; crédito
`MULTA_PAGADA` a Rentabilidad. Criterios: solo el pago genera el asiento.
*(RN-052)*

**RF-603 (M, ADM) — Anular multa.** Estado → `Anulada` con justificación
obligatoria auditada. Criterios: una multa pagada no puede anularse (se
revierte con RF-305 si fue un error). *(RN-051, RN-061)*

## 700 — Liquidación

**RF-701 (M, ADM) — Iniciar proceso de liquidación.** Solo desde
`PendienteLiquidacion`. Ejecuta pre-validaciones y muestra bloqueos: préstamos
sin pagar sin decisión, actividades abiertas, períodos sin conciliar.
*(RN-070, RN-071, RN-081)*

**RF-702 (M, ADM) — Resolver bloqueos con decisión.** Cada excepción (p. ej.
préstamo incobrable) exige decisión explícita con motivo, auditada. *(RN-071)*

**RF-703 (M, SYS) — Calcular liquidación.** Aplica la estrategia de
distribución configurada y la fórmula por participante. Criterios: suma de
participaciones == saldo de Rentabilidad, exacto (regla de redondeo RN-073);
el cálculo es reproducible: mismos insumos → mismo resultado. *(RN-072, RN-073)*

**RF-704 (M, ADM) — Revisar y confirmar liquidación.** Vista de revisión por
participante antes de confirmar. Confirmación con doble verificación
(escribir el nombre de la natillera). Criterios: irreversible; genera asientos
de cierre (`DEVOLUCION_AHORRO`, `DISTRIBUCION_RENTABILIDAD`) y transiciona la
natillera a `Liquidada`. *(RN-074, RN-080)*

**RF-705 (M, SYS) — Generar acta de liquidación.** Documento exportable (PDF)
con el detalle por participante y totales de control. *(RN-070; visión §9)*

**RF-706 (M, ADM/SUP) — Registrar entrega de efectivo.** Tras la liquidación,
registra la entrega física del saldo final a cada participante (firma/soporte
opcional). Único movimiento admisible en `Liquidada`. *(RN-074, RN-081)*

## 800 — Contabilidad y auditoría

**RF-801 (M, SYS) — Ledger append-only.** El repositorio de asientos no expone
update/delete; toda escritura pasa por `Fondo.validar_asiento`. Criterios: un
concepto no permitido para el fondo lanza error de dominio y aborta la
transacción completa. *(RN-060, RN-004, RN-005)*

**RF-802 (M, SYS) — Reconciliación de saldos.** Job programado que compara
saldos materializados vs suma de asientos por fondo y por participante.
Criterios: discrepancia → alerta crítica y bloqueo preventivo de operaciones
de egreso hasta resolución. *(RN-063)*

**RF-803 (M, ADM) — Consultar auditoría.** Búsqueda de asientos y acciones por
fecha, autor, participante, concepto, origen. *(RN-062)*

## 900 — Reportes y exportación

**RF-901 (M, ADM/SUP) — Reportes operativos.** Recaudo por período, cartera y
mora, rentabilidad acumulada por fuente (intereses/actividades/multas),
estado de la polla. Criterios: la apertura por fuente jamás incluye
`RETORNO_CAPITAL`. *(RN-034)*

**RF-902 (M, ADM/SUP/CLI) — Exportar a Excel y PDF.** Estados de cuenta,
reportes y acta de liquidación, con formato es-CO. *(stack: xlsx, jspdf)*

## 1000 — Autenticación y administración

**RF-1001 (M) — Autenticación JWT.** Access + refresh con rotación; sesión por
rol. *(stack)*

**RF-1002 (M, ADM) — Gestión de usuarios del tenant.** Crear usuarios SUP y
CLI, vincular CLI a su participante, desactivar usuarios. Criterios: un CLI
solo puede estar vinculado a un participante de la misma natillera. *(TEC-02)*

**RF-1003 (F) — Onboarding self-service de natilleras.** Registro comercial de
nuevos tenants con planes. Fase 5 del roadmap.

## Requisitos no funcionales (resumen; detalle en doc 05)

| ID | Requisito |
|---|---|
| RNF-01 | Montos con `Decimal` extremo a extremo; error de redondeo acumulado = 0 en liquidación (TEC-01) |
| RNF-02 | Aislamiento de tenant verificado por tests: ningún endpoint devuelve datos de otra natillera (TEC-02) |
| RNF-03 | Toda operación financiera es transaccional (Unit of Work): o se registran todos sus asientos o ninguno |
| RNF-04 | Registro de un pago de cuota ≤ 3 interacciones de UI (visión §7) |
| RNF-05 | Logging estructurado con `request_id`; toda mutación trazable a usuario y hora (TEC-08) |
| RNF-06 | Pantallas operativas (pagos, sorteo) mobile-first (doc 06 §6) |
| RNF-07 | Accesibilidad WCAG AA según sistema de diseño (DIS-01..DIS-09) |

## Fuera de alcance del MVP (trazado a feature flags)

Donaciones, rendimientos bancarios, CDT, inversiones, otros ingresos
extraordinarios (RN-091); pagos digitales; app nativa; modo oscuro (doc 06 §5);
onboarding self-service (RF-1003).
