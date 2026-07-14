# 00 — Project Vision

| Campo | Valor |
|---|---|
| Proyecto | Plataforma de Administración de Natilleras |
| Versión del documento | 1.0 |
| Fecha | 2026-07-10 |
| Estado | Borrador — pendiente de aprobación |
| Audiencia | Product Owner, Arquitectura, Claude Code |

---

## 1. Resumen ejecutivo

Construir una plataforma web comercial, multi-tenant y escalable para la
administración integral de natilleras colombianas: fondos de ahorro comunitario
informales que operan exclusivamente en efectivo, típicamente durante un ciclo
anual que finaliza con la devolución de ahorros y el reparto de la rentabilidad
generada internamente.

El producto no es una herramienta para una sola natillera: es una plataforma
capaz de administrar cientos o miles de natilleras de forma configurable,
auditable y confiable.

## 2. Problema

Las natilleras se administran hoy con cuadernos, hojas de cálculo o memoria del
administrador. Esto produce:

- **Opacidad financiera.** Los participantes no pueden verificar su estado de
  cuenta ni la rentabilidad acumulada; la confianza recae en una sola persona.
- **Errores de cálculo.** Intereses de préstamos, multas y utilidades de
  actividades se calculan a mano; la liquidación anual es propensa a disputas.
- **Mezcla de dineros.** Sin separación formal entre el ahorro de los
  participantes y la rentabilidad generada, es fácil (accidental o
  intencionalmente) usar dinero que no corresponde.
- **Sin trazabilidad.** No existe un registro auditable de movimientos; ante
  un reclamo, no hay evidencia.
- **Carga operativa.** Clonar la polla cada mes, controlar quién pagó, sortear
  solo entre pagadores y calcular utilidades es trabajo manual repetitivo.

## 3. Oportunidad

La natillera es una institución cultural masiva en Colombia sin una solución de
software dominante que respete sus reglas reales (efectivo, ciclo anual, polla,
multas, liquidación). Una plataforma que modele fielmente el negocio y ofrezca
transparencia verificable tiene potencial comercial: el administrador paga por
orden y protección; el participante gana visibilidad.

## 4. Visión del producto

> Ser la plataforma de referencia para administrar natilleras en Colombia,
> garantizando por diseño la separación de fondos, la trazabilidad total de
> cada peso y una liquidación anual sin disputas.

Principios de producto derivados:

1. **La confianza es la funcionalidad principal.** Cada peso es rastreable a un
   asiento inmutable en un ledger auditable.
2. **El software modela el negocio real, no lo simplifica.** Efectivo, polla
   con números anuales, multas, clonación mensual: el dominio manda.
3. **Configurable, no programado a la medida.** Cada natillera define sus
   cuotas, tasas, multas y actividades sin cambios de código.
4. **Preparado para crecer.** Funcionalidades futuras (donaciones, CDT,
   rendimientos bancarios) entran por feature flags sin tocar el núcleo.

## 5. Usuarios y roles

| Rol | Descripción | Necesidades principales |
|---|---|---|
| Administrador | Dirige la natillera; responsable del efectivo | Registrar movimientos rápido, controlar mora, clonar actividades, liquidar sin errores |
| Supervisor | Apoya al administrador con permisos limitados | Consultar, registrar pagos, sin operaciones destructivas |
| Cliente (participante) | Miembro de la natillera | Ver su estado de cuenta, sus números de polla, su rentabilidad proyectada |

(El RBAC técnico se detalla en `05-backend-architecture.md`.)

## 6. Alcance del MVP

### Incluido

- Gestión de natilleras (multi-tenant) con máquina de estados:
  Borrador → Abierta → En operación → Pendiente de liquidación → Liquidada → Archivada.
- Participantes con estado de cuenta (cuenta corriente tipo ledger).
- Fondo de Ahorro y Fondo de Rentabilidad estrictamente separados.
- Cuotas de ahorro y aportes extraordinarios (configurables).
- Préstamos sobre el Fondo de Ahorro: capital retorna al ahorro, intereses a
  rentabilidad.
- Módulo genérico de Actividades (polla, rifa, bingo, bazar, venta, otro) con
  cálculo automático de utilidad y clonación mensual.
- Polla con números anuales, participación condicionada al pago y sorteo solo
  entre números activos.
- Multas (mora en cuotas, préstamos y actividades); solo las pagadas generan
  rentabilidad.
- Liquidación anual como proceso validado e irreversible.
- Auditoría completa de movimientos.
- Reportes y exportación (Excel/PDF).

### Excluido del MVP (preparado vía feature flags)

- Donaciones como ingreso de rentabilidad.
- Rendimientos bancarios, CDT, inversiones.
- Otros ingresos extraordinarios.
- Pagos digitales / pasarelas (la natillera es 100% efectivo).
- App móvil nativa.

## 7. Métricas de éxito del MVP

| Métrica | Objetivo |
|---|---|
| Liquidación anual sin ajustes manuales | 100% de natilleras piloto |
| Descuadre entre ledger y saldos derivados | 0 pesos, siempre |
| Tiempo de clonación de actividad mensual | < 1 minuto |
| Registro de un pago de cuota | ≤ 3 interacciones de UI |
| Adopción piloto | ≥ 5 natilleras reales en el primer ciclo |

## 8. Restricciones y supuestos

- Operación 100% en efectivo; el sistema registra, no mueve dinero.
- Ciclo típico anual (dic–nov o ene–dic), configurable por natillera.
- Conectividad intermitente de algunos administradores: la UI debe ser
  eficiente en registrar operaciones en lote (p. ej. pagos del día).
- Moneda única: COP. Multi-moneda fuera de alcance.
- Normativa: la natillera es informal; el sistema no emite productos
  financieros regulados. (Validación legal pendiente como riesgo.)

## 9. Riesgos principales

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Modelar mal la separación de fondos | Crítico — invalida el producto | Ledger inmutable + invariantes en dominio + tests de reconciliación |
| Scope creep hacia banca digital | Alto | Feature flags + este documento como contrato de alcance |
| Retrofit de multi-tenancy | Alto | `natillera_id` obligatorio desde la migración 001 |
| Errores de redondeo/float | Alto | `Decimal` extremo a extremo (TEC-01) |
| Disputas en liquidación | Medio | Proceso de liquidación con pre-validaciones y acta exportable |

## 10. Roadmap de alto nivel

1. **Fase 0 — Documentación** (actual): docs 00–09 aprobados.
2. **Fase 1 — Núcleo financiero:** tenancy, participantes, ledger, fondos, cuotas.
3. **Fase 2 — Préstamos y multas.**
4. **Fase 3 — Actividades y polla** (clonación, sorteo).
5. **Fase 4 — Liquidación, auditoría, reportes/exports.**
6. **Fase 5 — Endurecimiento comercial:** onboarding de natilleras, planes,
   feature flags de rentabilidades futuras.

## 11. Glosario mínimo

- **Natillera:** fondo de ahorro comunitario informal colombiano de ciclo anual.
- **Polla:** actividad tipo lotería interna con números asignados anualmente.
- **Cuota:** aporte periódico de ahorro del participante.
- **Liquidación:** proceso de cierre anual que devuelve ahorros y reparte
  rentabilidad.
- **Ledger:** libro de movimientos inmutable (append-only) que soporta toda la
  contabilidad del sistema.
