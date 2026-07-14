# CLAUDE.md — Plataforma de Administración de Natilleras

Este archivo define las reglas que Claude Code debe respetar en TODAS las sesiones.
Las reglas marcadas como **INVARIANTE** son innegociables: ninguna funcionalidad nueva,
refactor o corrección puede violarlas. Si una tarea parece requerir romper un invariante,
DETENTE y pregunta antes de escribir código.

---

## 1. Qué es este proyecto

Plataforma comercial multi-tenant para administrar natilleras colombianas
(fondos de ahorro comunitario que operan 100% en efectivo). No es un CRUD:
es un producto diseñado para administrar cientos o miles de natilleras.

La documentación completa vive en `/docs`. Orden de lectura obligatorio antes
de implementar cualquier módulo:

1. `docs/01-business-rules.md` — reglas de negocio (fuente de verdad)
2. `docs/02-domain-model.md` — entidades, agregados, value objects
3. `docs/05-backend-architecture.md` — capas y patrones
4. El documento específico del módulo a implementar

**No generar código de un módulo cuya documentación no esté aprobada.**

---

## 2. INVARIANTES DE NEGOCIO (nunca romper)

### Fondos

- **INV-01 — Separación absoluta de fondos.** Existen dos fondos por natillera:
  Fondo de Ahorro y Fondo de Rentabilidad. Ningún movimiento puede transferir
  dinero de uno a otro fuera de los flujos definidos abajo. No existe ningún
  caso de uso que los mezcle.
- **INV-02 — Fondo de Ahorro.** Solo recibe: cuotas de ahorro y aportes
  extraordinarios. Nunca genera rentabilidad. Se devuelve a los participantes
  en la liquidación.
- **INV-03 — Fondo de Rentabilidad.** Solo recibe: intereses de préstamos
  pagados, utilidades de actividades y multas pagadas. Nunca recibe cuotas
  ni capital de préstamos.

### Préstamos

- **INV-04 — El capital nunca genera utilidad.** El capital prestado sale del
  Fondo de Ahorro y regresa íntegro al Fondo de Ahorro. Solo los intereses
  van al Fondo de Rentabilidad.

### Actividades

- **INV-05 — Módulo genérico.** No existe un módulo "Polla". Existe `Actividad`
  con tipos (polla, rifa, bingo, bazar, venta, otro). Todas comparten estructura.
- **INV-06 — Utilidad automática.** Utilidad = Ingresos − Premios − Gastos.
  Se transfiere automáticamente al Fondo de Rentabilidad al cerrar la actividad.
- **INV-07 — Solo números pagados participan.** En un sorteo solo son elegibles
  los números cuyo pago está registrado. Un número asignado pero no pagado está
  inactivo y NUNCA puede ganar. Validar en el dominio, no solo en la UI.
- **INV-08 — Números anuales.** Los números de la polla permanecen asignados
  todo el año. La clonación mensual copia participantes, números, configuración,
  premio y valor; NUNCA copia pagos, ganador, sorteo, evidencias ni auditoría.
- **INV-09 — Sorteo sin ganador.** Si ningún número activo gana, toda la
  utilidad pasa al Fondo de Rentabilidad.

### Multas

- **INV-10 — Solo multas PAGADAS generan rentabilidad.** Una multa registrada
  pero no pagada no suma al Fondo de Rentabilidad.

### Contabilidad y auditoría

- **INV-11 — Ledger inmutable (append-only).** Todo movimiento financiero es un
  asiento en la cuenta corriente del participante y/o del fondo. Los asientos
  NUNCA se actualizan ni se eliminan (`UPDATE`/`DELETE` prohibidos). Las
  correcciones se hacen con asientos de reversión.
- **INV-12 — Saldos derivados.** El saldo de un fondo o participante se deriva
  del ledger. Si existe una columna de saldo materializado, es solo caché y debe
  ser reconciliable con la suma de asientos.
- **INV-13 — Todo movimiento queda auditado.** Cada asiento registra: quién,
  cuándo, concepto, fondo afectado, referencia al origen (préstamo, actividad,
  multa, cuota).

### Liquidación y estados

- **INV-14 — La liquidación es un proceso, no un botón.** Calcula por
  participante: ahorros + rentabilidad − préstamos pendientes − intereses
  pendientes − multas pendientes = saldo final. Requiere validaciones previas
  y es irreversible una vez confirmada.
- **INV-15 — Máquina de estados de la natillera.**
  `Borrador → Abierta → En operación → Pendiente de liquidación → Liquidada → Archivada`.
  Las transiciones solo pueden avanzar en ese orden. Cada estado restringe qué
  operaciones son válidas (definido en `docs/01-business-rules.md`).

### Alcance

- **INV-16 — Solo efectivo.** No existen cuentas bancarias, CDT, inversiones ni
  rendimientos externos en el MVP. Estas funcionalidades futuras entran solo
  por feature flags y NO deben implementarse ahora, solo dejar los puntos de
  extensión definidos en la arquitectura.

---

## 3. REGLAS TÉCNICAS INNEGOCIABLES

- **TEC-01 — Dinero = `Decimal`, jamás `float`.** Python: `decimal.Decimal`.
  MySQL: `DECIMAL(15,2)`. Pydantic: `condecimal`/`Decimal`. TypeScript: manejar
  montos como string o entero en centavos, nunca aritmética con `number` flotante
  para dinero.
- **TEC-02 — Multi-tenancy desde la migración 001.** Toda tabla de negocio lleva
  `natillera_id` (tenant). El repositorio base aplica el filtro de tenant de
  forma obligatoria; ningún query de negocio puede omitirlo.
- **TEC-03 — Lógica de negocio en el dominio.** Nunca en routers/controladores
  de FastAPI. Capas: `api → services → domain → repositories → models`.
  Los services orquestan; los invariantes viven en entidades y value objects
  del paquete `domain/` (Python puro, sin FastAPI ni SQLAlchemy).
- **TEC-04 — Value objects obligatorios** para `Dinero`, `TasaInteres`,
  `NumeroPolla`, `Documento`. Validan en construcción.
- **TEC-05 — Domain events** para hechos de negocio relevantes
  (`InteresPagado`, `ActividadCerrada`, `MultaPagada`, `NatilleraLiquidada`).
  Los traspasos al Fondo de Rentabilidad se disparan por eventos, no por
  llamadas directas dispersas.
- **TEC-06 — Feature flags** vía `pydantic-settings` (clase `FeatureFlags`).
  Donaciones, rendimientos bancarios, CDT e inversiones quedan detrás de flags
  apagados.
- **TEC-07 — Tests financieros contra MySQL real.** Los tests de ledger,
  fondos y liquidación corren contra MySQL (Docker), no SQLite. SQLite solo
  para tests rápidos de API sin aritmética monetaria.
- **TEC-08 — Errores y logging.** Formato de error uniforme con exception
  handlers globales. Logging estructurado JSON (structlog) con `request_id`.
- **TEC-09 — Migraciones solo con Alembic.** Nunca `create_all` en producción.
  Ninguna migración destruye datos del ledger.

### Stack congelado

Backend: Python 3.12, FastAPI 0.115.6, SQLAlchemy 2.0.36 (Mapped), Alembic
1.14.0, Pydantic v2, PyMySQL, PyJWT (access+refresh), Passlib[bcrypt],
structlog, pytest + httpx.
Frontend: React 18.3 + TypeScript 5.7 strict, Vite 6, react-router-dom 6.28,
TanStack Query 5, Zustand 5, Axios (interceptor + refresh), React Hook Form,
TailwindCSS 3.4 (fuente Inter), lucide-react, xlsx, jspdf.
Infra: Docker Compose (MySQL 8 + app multi-stage con Nginx + supervisord),
migraciones en el entrypoint, volumen persistente.
RBAC: Administrador / Supervisor / Cliente por dependencias de FastAPI.

**No introducir dependencias nuevas sin justificarlo y pedir aprobación.**

---

## 4. Forma de trabajo con Claude Code

1. Antes de implementar, leer la documentación del módulo en `/docs`.
2. Proponer un plan (Plan Mode) y esperar aprobación en tareas que toquen
   dominio financiero, migraciones o el ledger.
3. Toda PR/commit referencia el requisito (`RF-xxx`) o regla (`RN-xxx`) que
   implementa.
4. Si una regla de negocio parece ambigua o contradictoria, preguntar; nunca
   asumir ni reinterpretar.
5. Los invariantes INV-01 a INV-16 deben tener tests que los protejan. Un
   refactor que rompa uno de esos tests está mal por definición.
