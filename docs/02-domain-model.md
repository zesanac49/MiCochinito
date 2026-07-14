# 02 — Domain Model

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026-07-10 |
| Estado | Borrador — pendiente de aprobación |
| Insumos | `01-business-rules.md` v1.1 (con decisiones PA-01..PA-05) |
| Convención | Los nombres del dominio se escriben en español (lenguaje ubicuo del negocio). El código usará estos mismos nombres. |

---

## 1. Lenguaje ubicuo

| Término | Definición precisa |
|---|---|
| Natillera | Agregado raíz del tenant. Fondo de ahorro comunitario de ciclo anual. |
| Ciclo | Período de vida operativo de una natillera (típicamente anual). |
| Participante | Persona inscrita en una natillera. Identidad local al tenant. |
| Fondo | Bolsa contable con reglas de ingreso/egreso. Solo existen dos tipos. |
| Asiento | Registro inmutable de un hecho financiero (débito o crédito). |
| Cuota | Aporte periódico de ahorro configurado por la natillera. |
| Actividad | Evento generador de rentabilidad (polla, rifa, bingo, bazar, venta, otro). |
| Período de actividad | Instancia mensual de una actividad recurrente (creada por clonación). |
| Número | Ficha de participación en una polla, asignada anualmente a un participante. |
| Multa | Sanción monetaria; es cuenta por cobrar hasta que se paga. |
| Liquidación | Proceso de cierre del ciclo: devolución de ahorros + distribución de rentabilidad. |

## 2. Contextos y módulos

Monolito modular con límites explícitos (bounded contexts ligeros). Cada módulo
tiene su paquete `domain/` independiente; la comunicación entre módulos es por
eventos de dominio o por servicios de aplicación, nunca por imports cruzados de
entidades.

```
┌──────────────────────────────────────────────────────────────┐
│                     GESTIÓN DE NATILLERAS                     │
│  Natillera · Configuración · Máquina de estados · Tenancy     │
└──────────────┬───────────────────────────────────────────────┘
               │ define el tenant y la configuración para todos
┌──────────────┴───────────┐  ┌────────────────────────────────┐
│      PARTICIPANTES       │  │      CONTABILIDAD (núcleo)      │
│ Participante · Estados   │  │ Ledger · Asiento · Fondos ·     │
│                          │  │ CuentaCorriente · Saldos        │
└──────────────┬───────────┘  └───────────────┬────────────────┘
               │ todos los módulos escriben SOLO vía Contabilidad
┌──────────────┴───────┐ ┌───────────────┐ ┌──┴─────────────────┐
│      PRÉSTAMOS       │ │  ACTIVIDADES  │ │       MULTAS        │
│ Prestamo · Pago ·    │ │ Actividad ·   │ │ Multa · Catálogo    │
│ PlanIntereses        │ │ Numero · Sorteo│ │                    │
└──────────────────────┘ └───────────────┘ └────────────────────┘
┌──────────────────────────────────────────────────────────────┐
│                        LIQUIDACIÓN                            │
│  Proceso · EstrategiaDistribucion · Acta                      │
└──────────────────────────────────────────────────────────────┘
```

Regla estructural clave: **Contabilidad es el único módulo que escribe
asientos.** Préstamos, Actividades, Multas y Liquidación producen eventos u
órdenes contables; nunca insertan en el ledger directamente. Así los
invariantes INV-01..INV-03 viven en un solo lugar.

## 3. Value Objects

Todos inmutables, validan en construcción, con igualdad por valor.

| VO | Contenido | Invariantes |
|---|---|---|
| `Dinero` | `monto: Decimal`, moneda fija COP | `Decimal` con 2 decimales; operaciones solo entre `Dinero`; prohíbe construcción desde `float` (TEC-01) |
| `TasaInteres` | `porcentaje: Decimal`, base mensual | 0 < tasa ≤ tope configurado |
| `Documento` | tipo (CC, CE, TI, PP) + número | formato válido por tipo; único por natillera (RN-011) |
| `NumeroPolla` | valor entero | 1 ≤ n ≤ cantidad configurada de la polla |
| `Periodo` | año + mes | dentro del ciclo de la natillera |
| `ConceptoContable` | enum cerrado | ver §5; determina fondo destino/origen |
| `ReferenciaOrigen` | tipo de agregado + id | todo asiento apunta a su origen (RN-062) |

## 4. Agregados

### 4.1 Natillera (raíz de tenancy)

- **Atributos:** nombre, ciclo (fechas inicio/fin), estado, configuración.
- **Configuración (entidad interna):** valor y periodicidad de cuota; habilita
  aportes extraordinarios (RN-021); tasa de interés base y límites (RN-031);
  tope de préstamos concurrentes (RN-037, default 2); monto máximo de capital
  vigente por participante (RN-038); catálogo de multas (RN-050); estrategia
  de distribución de rentabilidad (RN-073); feature flags heredados del
  sistema (RN-091).
- **Máquina de estados (RN-080):**
  `Borrador → Abierta → EnOperacion → PendienteLiquidacion → Liquidada → Archivada`.
  El agregado expone `puede(operacion)` consultado por todos los módulos
  (matriz RN-081). Transiciones emiten eventos (`NatilleraAbierta`, etc.).
- **Invariantes:** los cambios de configuración rigen hacia futuro (RN-020);
  la estrategia de distribución se congela al entrar a `PendienteLiquidacion`.

### 4.2 Participante

- **Atributos:** nombre, `Documento`, teléfono, dirección, estado
  (`Activo | Suspendido | Retirado`), fecha de ingreso (insumo de la
  estrategia de distribución ponderada por tiempo).
- **Invariantes:** nunca se elimina físicamente (RN-012); `Documento` único en
  el tenant.
- Su "estado de cuenta" NO es parte de este agregado: es una proyección del
  ledger (módulo Contabilidad), evitando un agregado gigante.

### 4.3 Ledger y Fondos (módulo Contabilidad — el corazón)

- **`Asiento` (entidad inmutable):** id, fecha/hora, autor, `Dinero`,
  naturaleza (`Debito | Credito`), fondo afectado, participante (opcional),
  `ConceptoContable`, `ReferenciaOrigen`, asiento revertido (opcional, RN-061).
  Sin métodos de mutación. El repositorio no expone update/delete (RN-060).
- **`Fondo` (agregado):** tipo (`Ahorro | Rentabilidad`), natillera. Su saldo
  es derivado (RN-063); puede materializar caché reconciliable.
  - Método central: `validar_asiento(asiento)` — implementa la matriz de
    conceptos permitidos (§5). Un concepto no permitido lanza
    `ViolacionSeparacionDeFondos` (excepción de dominio). Aquí viven
    INV-01..INV-03 como código.
- **`CuentaCorriente` (proyección):** vista por participante de sus asientos
  con saldo por concepto (ahorros, deuda de capital, intereses pendientes,
  multas pendientes). Solo lectura.

### 4.4 Prestamo

- **Atributos:** participante, capital (`Dinero`), fecha desembolso, plazo,
  `TasaInteres`, estado.
- **Estados (RN-032):** `Solicitado → Aprobado → Desembolsado → EnPago →
  Pagado`; salidas: `Rechazado` (pre-desembolso), `EnMora` ↔ `EnPago`.
- **Entidad interna `PagoPrestamo`:** monto recibido, descomposición
  capital/interés calculada por el agregado. Emite `PagoPrestamoRegistrado`
  con ambos componentes; Contabilidad genera dos asientos (RN-033): capital →
  crédito Fondo Ahorro; interés → crédito Fondo Rentabilidad.
- **Invariantes:** desembolso exige saldo suficiente del Fondo de Ahorro
  (RN-007/RN-030), tope de concurrencia (RN-037) y tope de capital vigente
  (RN-038); ninguna consulta de rentabilidad incluye capital (RN-034); el
  interés causado no pagado nunca genera asiento en Rentabilidad (RN-035).

### 4.5 Actividad

- **Atributos:** tipo (`Polla | Rifa | Bingo | Bazar | Venta | Otro`; `Donacion`
  reservado tras flag), período, configuración, estado, colecciones de
  ingresos, gastos y premios.
- **Estados (RN-043):** `Borrador → Abierta → Sorteada/Realizada → Cerrada`.
- **Cálculo:** `utilidad() = ingresos − premios − gastos` (RN-041); método, no
  campo editable.
- **Cierre:** emite `ActividadCerrada(utilidad)`. Contabilidad acredita
  Rentabilidad; si utilidad < 0, debita Rentabilidad previa validación de
  saldo (RN-042a). El Fondo de Ahorro es inalcanzable desde este flujo.
- **Especialización Polla (entidad interna `AsignacionNumeros`):**
  - `Numero`: `NumeroPolla` + participante + estado de pago del período.
  - `numeros_activos(periodo)`: solo con pago registrado (RN-046, pago mensual
    por decisión PA-04).
  - `sortear(numero_ganador)`: opera únicamente sobre activos (RN-047); si el
    ganador no está activo → `SorteoSinGanador` y la utilidad íntegra va a
    Rentabilidad (RN-048).
  - `clonar_para(periodo)`: copia participantes, números, configuración,
    premio, valor; excluye pagos, ganador, sorteo, evidencias, auditoría;
    estado inicial `Borrador` (RN-049). Es un Factory method del agregado.

### 4.6 Multa

- **Atributos:** participante, tipo (del catálogo), valor (`Dinero`), motivo,
  referencia (cuota/préstamo/actividad), estado.
- **Estados (RN-051):** `Impuesta → Pagada | Anulada` (anulación con
  justificación auditada).
- Solo `Pagada` emite `MultaPagada` → crédito a Rentabilidad (RN-052).

### 4.7 Liquidacion (proceso como agregado)

- **Fases (RN-070):** `PreValidacion → Calculada → EnRevision → Confirmada →
  ActaGenerada`. Irreversible desde `Confirmada` (RN-074).
- **Pre-validaciones (RN-071):** préstamos no pagados sin decisión, actividades
  abiertas, períodos sin conciliar → lista de bloqueos; excepciones requieren
  decisión explícita auditada.
- **Cálculo por participante (RN-072):**
  `saldo_final = ahorros + participacion_rentabilidad − capital_pendiente −
  intereses_pendientes − multas_pendientes`.
- **`EstrategiaDistribucion` (Strategy — decisión PA-01):** interfaz
  `distribuir(fondo_rentabilidad, participantes) → dict[participante, Dinero]`.
  Implementaciones MVP: `PartesIguales`, `ProporcionalAlAhorro`,
  `ProporcionalPonderadaPorTiempo`. Postcondición verificada por el proceso:
  `sum(participaciones) == saldo_fondo` exacto; el residuo de redondeo se
  asigna al participante de mayor participación (RN-073).
- **Salida:** asientos de cierre + `Acta` (documento exportable) +
  `NatilleraLiquidada`.

## 5. Matriz de conceptos contables (la separación de fondos como dato)

Esta matriz ES el invariante INV-01..INV-03 en forma verificable. Vive en el
dominio de Contabilidad y tiene tests exhaustivos.

| `ConceptoContable` | Fondo Ahorro | Fondo Rentabilidad |
|---|---|---|
| `CUOTA_AHORRO` | Crédito | ✗ |
| `APORTE_EXTRAORDINARIO` | Crédito | ✗ |
| `DESEMBOLSO_PRESTAMO` | Débito | ✗ |
| `RETORNO_CAPITAL` | Crédito | ✗ |
| `INTERES_PAGADO` | ✗ | Crédito |
| `UTILIDAD_ACTIVIDAD` | ✗ | Crédito |
| `PERDIDA_ACTIVIDAD` (RN-042a) | ✗ | Débito |
| `MULTA_PAGADA` | ✗ | Crédito |
| `DEVOLUCION_AHORRO` (liquidación) | Débito | ✗ |
| `DISTRIBUCION_RENTABILIDAD` (liquidación) | ✗ | Débito |
| `REVERSION` | Espejo del asiento revertido | Espejo del asiento revertido |

Conceptos futuros tras feature flag (RN-091): `DONACION`, `RENDIMIENTO_BANCARIO`,
`RENDIMIENTO_CDT`, `RENDIMIENTO_INVERSION` — todos exclusivamente Crédito a
Rentabilidad. La matriz se extiende; las filas existentes jamás cambian.

## 6. Eventos de dominio

| Evento | Emisor | Consumidor principal | Efecto contable |
|---|---|---|---|
| `CuotaPagada` | Participantes/Cuotas | Contabilidad | Crédito Ahorro |
| `PrestamoDesembolsado` | Prestamo | Contabilidad | Débito Ahorro |
| `PagoPrestamoRegistrado` | Prestamo | Contabilidad | Crédito Ahorro (capital) + Crédito Rentabilidad (interés) |
| `PrestamoEnMora` | Prestamo | Multas | Impone multa según catálogo |
| `ActividadCerrada` | Actividad | Contabilidad | Crédito/Débito Rentabilidad |
| `SorteoSinGanador` | Actividad (Polla) | Contabilidad | Utilidad íntegra a Rentabilidad |
| `MultaPagada` | Multa | Contabilidad | Crédito Rentabilidad |
| `NatilleraLiquidada` | Liquidacion | Contabilidad, Notificaciones (futuro) | Asientos de cierre |

Implementación MVP: bus de eventos síncrono en memoria dentro de la misma
transacción (Unit of Work). La interfaz del bus permite migrar a despacho
asíncrono sin tocar el dominio.

## 7. Trazabilidad reglas → modelo

| Invariante | Dónde vive en el modelo |
|---|---|
| INV-01..03 (separación de fondos) | `Fondo.validar_asiento` + matriz §5 |
| INV-04 (capital sin utilidad) | Descomposición en `PagoPrestamo`; consultas de rentabilidad excluyen `RETORNO_CAPITAL` por construcción |
| INV-05..09 (actividades/polla) | Agregado `Actividad` + `AsignacionNumeros` |
| INV-10 (multas pagadas) | Estado de `Multa`; solo `Pagada` emite evento |
| INV-11..13 (ledger) | `Asiento` inmutable + repositorio append-only |
| INV-14 (liquidación proceso) | Agregado `Liquidacion` con fases |
| INV-15 (estados natillera) | Máquina de estados en `Natillera.puede()` |
| INV-16 (solo efectivo) | Matriz §5 cerrada + feature flags |

## 8. Decisiones de modelado justificadas

1. **Contabilidad como módulo único de escritura al ledger.** Alternativa
   descartada: que cada módulo escriba sus asientos. Centralizar hace que la
   separación de fondos sea un invariante de un solo agregado, testeable en un
   solo lugar.
2. **Saldos derivados con caché reconciliable** en vez de columna mutable de
   saldo. Costo: queries de agregación; mitigación: caché materializada +
   job de reconciliación. Beneficio: descuadre imposible de ocultar.
3. **Polla como especialización interna de Actividad** y no subclase pública.
   Mantiene el módulo genérico (INV-05) y permite futuros tipos con mecánica
   propia (bingo con cartones) sin romper la interfaz.
4. **Strategy para distribución** (PA-01): agregar una estrategia nueva no
   toca la liquidación; solo se registra una implementación más.
5. **Bus de eventos síncrono en MVP.** Event-driven donde aporta (traspasos a
   Rentabilidad) sin la complejidad operativa de colas; la interfaz deja la
   puerta abierta (criterio del brief: "event driven cuando sea conveniente").
