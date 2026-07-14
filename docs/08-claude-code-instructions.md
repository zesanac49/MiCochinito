# 08 — Claude Code Instructions

| Campo | Valor |
|---|---|
| Versión | 1.0 |
| Fecha | 2026-07-10 |
| Estado | Borrador — pendiente de aprobación |
| Relación con CLAUDE.md | `CLAUDE.md` (raíz) contiene los invariantes SIEMPRE presentes. Este documento define el proceso de trabajo detallado. |

---

## 1. Jerarquía de fuentes de verdad

Ante cualquier conflicto, el orden de precedencia es:

1. `CLAUDE.md` (invariantes INV / reglas TEC)
2. `docs/01-business-rules.md` (reglas RN)
3. `docs/02-domain-model.md` a `docs/07-api-design.md`
4. Código existente
5. Criterio propio de Claude Code

Si el nivel 5 detecta un conflicto entre niveles superiores: **no resolverlo
por cuenta propia; reportar y preguntar.**

## 2. Flujo de trabajo por tarea

1. **Leer** la issue (Linear) y los documentos referenciados (RF/RN).
2. **Plan Mode obligatorio** cuando la tarea toque: dominio de contabilidad,
   migraciones, cualquier flujo que genere asientos, liquidación, o cambios a
   máquinas de estado. Esperar aprobación del plan antes de codificar.
3. **Implementar** respetando la estructura de paquetes (doc 05 §3): dominio
   primero, luego caso de uso, luego infraestructura, luego endpoint.
4. **Tests antes de terminar** (ver Definition of Done). Los tests de
   invariantes (`test_inv_XX_*`) existentes NUNCA se modifican para hacerlos
   pasar; si uno falla, el código nuevo está mal.
5. **Commit** con convención (§4) referenciando RF/RN e issue.
6. Si durante la implementación surge una regla no documentada o ambigua:
   detenerse, documentar la pregunta y esperar respuesta. Prohibido inventar
   reglas de negocio.

## 3. Definition of Done (por tarea)

- [ ] Lógica de negocio en `domain/`; router ≤ ~15 líneas; sin imports
      prohibidos (verificable con import-linter).
- [ ] Tests: unit de dominio para toda regla nueva; integración MySQL si la
      tarea escribe asientos; test de tenancy si expone endpoint nuevo.
- [ ] Ningún `float` en rutas de dinero (grep de guardia en CI: `float(` en
      módulos de dominio = fallo).
- [ ] Errores mapeados al catálogo del doc 07 §4 (sin códigos nuevos sin
      aprobación).
- [ ] Logging del caso de uso con `request_id`.
- [ ] Migración Alembic reversible si toca esquema; jamás toca datos del
      ledger.
- [ ] OpenAPI actualizado coincide con doc 07 (o doc 07 actualizado en el
      mismo PR con nota de cambio).
- [ ] `docs/` actualizado si la tarea cambió una decisión (con nueva versión
      del documento afectado).

## 4. Convenciones de código y commits

- **Idioma:** dominio en español (lenguaje ubicuo, doc 02 §1); comentarios y
  docstrings en español; nombres técnicos genéricos (repos, uow) pueden ser
  ingleses estándar.
- **Commits:** `tipo(modulo): descripción — RF-xxx/RN-xxx (LIN-123)`.
  Tipos: feat, fix, test, refactor, docs, chore, migration.
- **Ramas:** `feature/LIN-123-descripcion-corta`; PRs pequeños, un RF (o
  fracción coherente) por PR.
- **Estilo Python:** ruff + mypy strict en `domain/` y `application/`.
  **TypeScript:** strict, sin `any` en código nuevo.
- **Dinero en frontend:** los montos llegan como string; se muestran con el
  formateador es-CO central (`formatoCOP`); prohibida la aritmética de montos
  en el cliente — todo cálculo lo hace la API.

## 5. Errores conocidos a evitar (lecciones pre-cargadas)

- No usar `float` "temporalmente". No existe temporalmente.
- No agregar `UPDATE` al repo del ledger "solo para este caso".
- No copiar pagos/sorteo al clonar actividades "para ahorrar pasos".
- No permitir que un service reciba `natillera_id` del body de la petición.
- No hacer commit de `.env` ni credenciales; secretos solo por entorno.
- No "simplificar" la doble verificación de la liquidación en desarrollo.
- No usar `create_all` ni editar migraciones ya aplicadas; siempre una nueva.

## 6. Qué hacer ante situaciones específicas

| Situación | Acción |
|---|---|
| El RF pide algo que viola un INV | Detenerse; reportar el conflicto citando ambos |
| Falta una regla (caso no cubierto) | Proponer 2–3 opciones con impacto; no elegir solo |
| Un test de invariante falla tras un cambio | Revertir el cambio, no el test |
| Se necesita una dependencia nueva | Justificar (qué resuelve, alternativas, licencia) y pedir aprobación |
| Bug en producción sobre datos del ledger | Corrección SOLO con asientos de reversión (RN-061); jamás SQL manual |
| Duda sobre alcance MVP | Consultar doc 00 §6; si el flag existe y está apagado, no implementar detrás |
