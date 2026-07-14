# 01 — Business Rules

| Campo | Valor |
|---|---|
| Versión | 1.1 — preguntas abiertas PA-01..PA-05 resueltas |
| Fecha | 2026-07-10 |
| Estado | Borrador — pendiente de aprobación |
| Precedencia | Este documento es la FUENTE DE VERDAD de negocio. Ante conflicto con cualquier otro documento o código, gana este. |

Convenciones:

- **RN-xxx** — regla de negocio. Obligatoria salvo que indique lo contrario.
- **Nivel de aplicación:** `DOMINIO` (invariante en código de dominio, con test),
  `PROCESO` (validación en caso de uso/servicio), `UI` (refuerzo visual, nunca
  única línea de defensa).
- Toda regla `DOMINIO` corresponde a uno o más invariantes del `CLAUDE.md`.

---

## 1. Fondos

**RN-001 — Dos fondos por natillera.** Toda natillera tiene exactamente un
Fondo de Ahorro y un Fondo de Rentabilidad. Se crean con la natillera y no
pueden eliminarse. *(DOMINIO — INV-01)*

**RN-002 — Ingresos permitidos al Fondo de Ahorro.** Únicamente: (a) cuotas de
ahorro, (b) aportes extraordinarios si la natillera los habilita, (c) retorno
de capital de préstamos. Cualquier otro concepto es rechazado. *(DOMINIO — INV-02)*

**RN-003 — Egresos permitidos del Fondo de Ahorro.** Únicamente: (a) desembolso
de capital de préstamos, (b) devolución de ahorros en la liquidación.
*(DOMINIO — INV-02)*

**RN-004 — Ingresos permitidos al Fondo de Rentabilidad.** Únicamente:
(a) intereses de préstamos efectivamente pagados, (b) utilidad de actividades
cerradas, (c) multas efectivamente pagadas. *(DOMINIO — INV-03)*

**RN-005 — Prohibición de transferencias entre fondos.** No existe ninguna
operación que mueva dinero del Fondo de Ahorro al de Rentabilidad ni viceversa.
Los flujos de RN-002/RN-004 no son transferencias entre fondos sino
clasificación en origen. *(DOMINIO — INV-01)*

**RN-006 — El Fondo de Ahorro nunca genera rentabilidad.** No se le imputan
intereses, valorizaciones ni rendimientos de ninguna clase. *(DOMINIO — INV-02)*

**RN-007 — Saldos no negativos.** Ningún fondo puede quedar con saldo negativo.
Toda operación de egreso valida saldo suficiente al momento de confirmarse.
*(DOMINIO)*

## 2. Participantes

**RN-010 — Pertenencia.** Todo participante pertenece a exactamente una
natillera (tenant). Una misma persona natural puede existir en varias
natilleras como participantes independientes. *(DOMINIO — TEC-02)*

**RN-011 — Datos mínimos.** Nombre, documento de identidad, teléfono,
dirección y estado. El documento es único dentro de la natillera. *(PROCESO)*

**RN-012 — Estados del participante.** `Activo`, `Suspendido`, `Retirado`.
Un participante `Retirado` conserva su historial y su estado de cuenta; no se
elimina físicamente jamás. *(DOMINIO)*

**RN-013 — Estado de cuenta.** Todo participante tiene una cuenta corriente
compuesta exclusivamente por asientos del ledger (RN-060). *(DOMINIO — INV-11)*

## 3. Cuotas y aportes

**RN-020 — Cuota configurable.** Cada natillera define valor y periodicidad de
la cuota de ahorro. Cambios de configuración rigen hacia futuro; nunca
recalculan cuotas ya causadas. *(PROCESO)*

**RN-021 — Aportes extraordinarios.** Solo existen si la natillera los habilita
en su configuración. Ingresan al Fondo de Ahorro. *(DOMINIO — INV-02)*

**RN-022 — Mora en cuotas.** La cuota no pagada en la fecha límite puede
generar multa según la configuración de la natillera (ver RN-050). *(PROCESO)*

## 4. Préstamos

**RN-030 — Origen del capital.** Todo préstamo se desembolsa desde el Fondo de
Ahorro, sujeto a RN-007 (saldo suficiente). *(DOMINIO — INV-04)*

**RN-031 — Atributos del préstamo.** Capital, fecha de desembolso, plazo, tasa
de interés y estado. La tasa es configurable por natillera con posibilidad de
ajuste por préstamo dentro de límites configurados. *(PROCESO)*

**RN-032 — Estados del préstamo.** `Solicitado → Aprobado → Desembolsado →
En pago → Pagado` con salidas a `Rechazado` (antes de desembolso) y
`En mora` (desde En pago, reversible al ponerse al día). *(DOMINIO)*

**RN-033 — Destino de los pagos.** De cada pago recibido, la porción de capital
retorna al Fondo de Ahorro y la porción de interés ingresa al Fondo de
Rentabilidad. Un mismo pago genera asientos separados por componente.
*(DOMINIO — INV-04)*

**RN-034 — El capital jamás genera utilidad.** Ninguna fórmula de rentabilidad
puede incluir capital de préstamos. *(DOMINIO — INV-04)*

**RN-035 — Intereses pendientes no son rentabilidad.** Solo el interés
efectivamente pagado ingresa al Fondo de Rentabilidad. El interés causado y no
pagado se refleja como cuenta por cobrar del participante. *(DOMINIO — INV-03)*

**RN-036 — Mora en préstamos.** Genera multa según configuración (RN-050),
independiente del interés pactado. *(PROCESO)*

**RN-037 — Préstamos concurrentes con tope.** *(Decisión PA-03)* Un
participante puede tener varios préstamos activos simultáneamente, hasta el
tope de cantidad configurado por la natillera (por defecto: 2). *(DOMINIO)*

**RN-038 — Monto máximo por participante.** *(Decisión PA-05)* Cada natillera
configura un monto fijo máximo de capital prestado vigente por participante
(suma de saldos de capital de todos sus préstamos activos). Una solicitud que
exceda el tope se rechaza en el dominio. *(DOMINIO)*

## 5. Actividades

**RN-040 — Módulo genérico.** Existe una única entidad `Actividad` con tipo:
`Polla`, `Rifa`, `Bingo`, `Bazar`, `Venta`, `Otro` (y `Donación` reservado
tras feature flag, fuera del MVP). Todas comparten la misma estructura de
ingresos, gastos, premios y utilidad. *(DOMINIO — INV-05)*

**RN-041 — Cálculo de utilidad.** `Utilidad = Ingresos − Premios − Gastos`.
Se calcula automáticamente; no es editable a mano. *(DOMINIO — INV-06)*

**RN-042 — Traspaso automático.** Al cerrar una actividad, su utilidad ingresa
automáticamente al Fondo de Rentabilidad mediante evento de dominio
(`ActividadCerrada`). *(DOMINIO — INV-06)*

**RN-042a — Pérdidas de actividades.** *(Decisión PA-02)* Si la utilidad es
negativa, la pérdida se absorbe contra la rentabilidad acumulada mediante un
asiento de débito al Fondo de Rentabilidad. El cierre con pérdida se
pre-valida contra RN-007: si la rentabilidad acumulada es insuficiente para
absorberla, el cierre se bloquea y requiere resolución del administrador
(registrar ingresos faltantes o ajustar gastos), quedando todo auditado.
El Fondo de Ahorro jamás absorbe pérdidas de actividades. *(DOMINIO — INV-01, INV-03)*

**RN-043 — Estados de la actividad.** `Borrador → Abierta → Sorteada/Realizada
→ Cerrada`. Solo actividades `Cerrada` afectan el Fondo de Rentabilidad.
*(DOMINIO)*

### Polla (tipo de actividad)

**RN-044 — Configuración de la polla.** Valor por número, cantidad de números,
premio y fecha del sorteo. *(PROCESO)*

**RN-045 — Números anuales.** Los números asignados a cada participante
permanecen fijos durante todo el ciclo de la natillera. La clonación mensual no
los reasigna. *(DOMINIO — INV-08)*

**RN-046 — Participación condicionada al pago.** Un número participa en el
sorteo si y solo si su pago del período está registrado. Números sin pago están
`Inactivos` para ese sorteo. *(DOMINIO — INV-07)*

**RN-047 — Sorteo solo entre activos.** El mecanismo de sorteo opera
exclusivamente sobre números activos. Es imposible por construcción que gane un
número sin pago. *(DOMINIO — INV-07)*

**RN-048 — Sorteo sin ganador.** Si el número sorteado no está entre los
activos (o la mecánica definida no produce ganador), la totalidad de la
utilidad del período pasa al Fondo de Rentabilidad. *(DOMINIO — INV-09)*

**RN-049 — Clonación mensual.** Al clonar una actividad se copian:
participantes, números asignados, configuración, premio y valor. NO se copian:
pagos, ganador, resultado del sorteo, evidencias ni auditoría. La actividad
clonada nace en estado `Borrador` y limpia. *(DOMINIO — INV-08)*

## 6. Multas

**RN-050 — Catálogo configurable.** Cada natillera configura tipos de multa
(mora en cuotas, mora en préstamos, mora en actividades, otras) con su valor o
fórmula. *(PROCESO)*

**RN-051 — Ciclo de la multa.** `Impuesta → Pagada` o `Impuesta → Anulada`
(la anulación exige justificación y queda auditada). *(DOMINIO)*

**RN-052 — Solo multas pagadas generan rentabilidad.** La multa impuesta es una
cuenta por cobrar; únicamente al registrarse su pago ingresa al Fondo de
Rentabilidad. *(DOMINIO — INV-10)*

## 7. Ledger y auditoría

**RN-060 — Ledger append-only.** Todo hecho financiero se registra como asiento
inmutable con débito/crédito. Prohibidos `UPDATE` y `DELETE` sobre asientos.
*(DOMINIO — INV-11)*

**RN-061 — Corrección por reversión.** Un error se corrige con un asiento de
reversión referenciando al original, más el asiento correcto. *(DOMINIO — INV-11)*

**RN-062 — Trazabilidad del asiento.** Cada asiento registra: fecha/hora, autor,
concepto, fondo afectado, participante (si aplica), y referencia al agregado de
origen (cuota, préstamo, actividad, multa, liquidación). *(DOMINIO — INV-13)*

**RN-063 — Saldos derivados y reconciliación.** Los saldos se derivan del
ledger. Cualquier saldo materializado (caché) debe poder reconciliarse contra
la suma de asientos; una discrepancia es un defecto crítico. *(DOMINIO — INV-12)*

## 8. Liquidación

**RN-070 — La liquidación es un proceso.** Consta de: (1) pre-validaciones,
(2) cálculo, (3) revisión por el administrador, (4) confirmación irreversible,
(5) generación de acta y asientos de cierre. *(DOMINIO — INV-14)*

**RN-071 — Pre-validaciones.** No puede iniciarse la liquidación si existen:
préstamos con estado distinto de `Pagado` sin decisión registrada, actividades
sin cerrar, o períodos de cuotas sin conciliar. Las excepciones requieren
decisión explícita del administrador y quedan auditadas. *(PROCESO)*

**RN-072 — Fórmula por participante.**
`Saldo final = Ahorros acumulados + Participación en rentabilidad − Capital de
préstamos pendiente − Intereses pendientes − Multas pendientes`. *(DOMINIO — INV-14)*

**RN-073 — Distribución de la rentabilidad configurable.** *(Decisión PA-01)*
Cada natillera configura su estrategia de distribución de la rentabilidad.
El MVP incluye tres estrategias intercambiables: (a) partes iguales entre
participantes activos, (b) proporcional al ahorro acumulado, (c) proporcional
al ahorro ponderado por tiempo de permanencia. La estrategia se fija en la
configuración de la natillera y no puede cambiarse una vez iniciada la
liquidación. La suma de participaciones debe ser exactamente igual al saldo
del Fondo de Rentabilidad (regla de redondeo: el residuo por redondeo se
asigna al participante de mayor participación). *(DOMINIO)*

**RN-074 — Irreversibilidad.** Confirmada la liquidación, la natillera pasa a
`Liquidada` y ningún movimiento posterior es admisible salvo asientos de
entrega de efectivo derivados del acta. *(DOMINIO — INV-15)*

## 9. Estados de la natillera

**RN-080 — Máquina de estados.**
`Borrador → Abierta → En operación → Pendiente de liquidación → Liquidada → Archivada`.
Sin saltos ni retrocesos. *(DOMINIO — INV-15)*

**RN-081 — Operaciones por estado.**

| Estado | Permitido | Prohibido |
|---|---|---|
| Borrador | Configurar, registrar participantes | Cualquier movimiento financiero |
| Abierta | Inscribir participantes, asignar números | Préstamos, sorteos |
| En operación | Toda la operación normal | Liquidar sin pasar por pendiente |
| Pendiente de liquidación | Cobros de cartera, cierre de actividades, liquidación | Nuevos préstamos, nuevas actividades |
| Liquidada | Consulta, exportes, asientos de entrega | Todo lo demás |
| Archivada | Solo consulta | Todo lo demás |

*(DOMINIO — INV-15)*

## 10. Alcance y extensibilidad

**RN-090 — Solo efectivo.** El sistema registra operaciones en efectivo. No
existen integraciones bancarias, CDT, inversiones ni rendimientos externos en
el MVP. *(DOMINIO — INV-16)*

**RN-091 — Extensiones tras feature flags.** Donaciones, rendimientos
bancarios, CDT, inversiones y otros ingresos extraordinarios se diseñan como
nuevos *tipos de ingreso al Fondo de Rentabilidad* activables por flag, sin
modificar RN-001 a RN-007. *(DOMINIO — TEC-06)*

---

## Registro de decisiones (preguntas abiertas resueltas — 2026-07-10)

| ID | Pregunta | Decisión | Regla resultante |
|---|---|---|---|
| PA-01 | Distribución de la rentabilidad | Configurable por natillera (3 estrategias en MVP) | RN-073 |
| PA-02 | Actividad con utilidad negativa | Absorber contra rentabilidad acumulada, sin saldo negativo | RN-042a |
| PA-03 | Préstamos activos simultáneos | Sí, con tope de cantidad configurable | RN-037 |
| PA-04 | Pago de la polla | Mensual, por período/clonación; participa quien pagó el período | RN-046 |
| PA-05 | Tope de monto de préstamo | Monto fijo configurable por participante (capital vigente) | RN-038 |

Con estas decisiones, `02-domain-model.md` queda desbloqueado.
