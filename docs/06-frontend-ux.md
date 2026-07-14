# 06 — Frontend UX: Dirección Visual y Sistema de Diseño

| Campo | Valor |
|---|---|
| Versión | 0.1 (dirección visual; los flujos UX se completan tras aprobar docs 02–03) |
| Fecha | 2026-07-10 |
| Estado | Borrador — pendiente de aprobación |
| Decisión de diseño | **Neomorfismo (Soft UI) adaptado a producto financiero** |

---

## 1. Concepto visual: Neomorfismo pragmático

La interfaz adopta el lenguaje neomórfico: superficies que parecen extruidas o
hundidas en un mismo material, mediante doble sombra (luz arriba-izquierda,
sombra abajo-derecha), esquinas muy redondeadas y una paleta monomaterial.

La metáfora encaja con el producto: la natillera es tangible, artesanal, de
efectivo que pasa de mano en mano. El soft UI transmite esa fisicalidad
(botones que se "hunden" al presionar, tarjetas que "sobresalen" del fondo)
sin caer en el skeuomorfismo literal.

### 1.1 Riesgos conocidos del neomorfismo (y cómo los neutralizamos)

El neomorfismo puro tiene tres problemas documentados que en una app financiera
serían graves. El sistema de diseño los resuelve por regla, no por criterio de
cada pantalla:

| Riesgo | Consecuencia | Regla que lo neutraliza |
|---|---|---|
| Bajo contraste (todo es el mismo material) | Jerarquía débil, fatiga, fallo WCAG | DIS-01, DIS-02 |
| Estados poco distinguibles (activo/inactivo/deshabilitado se parecen) | Errores al registrar dinero | DIS-03, DIS-04 |
| Ruido visual en densidad alta (tablas, ledger) | Ilegibilidad de datos financieros | DIS-05 |

## 2. Reglas del sistema de diseño (DIS-xxx)

**DIS-01 — Contraste de texto innegociable.** Todo texto cumple WCAG AA:
≥ 4.5:1 en texto normal, ≥ 3:1 en texto grande. El neomorfismo vive en las
superficies y sombras, jamás a costa del color del texto. Texto principal
`#1F2430` sobre base `#E8ECF1`.

**DIS-02 — Un acento fuerte.** El color de acento (verde esmeralda, ver
tokens) se reserva para: acción primaria de la pantalla, montos positivos
destacados y estados de éxito. Nunca más de una acción primaria visible por
vista.

**DIS-03 — El estado nunca depende solo de la sombra.** Interruptores, tabs y
botones comunican estado con sombra (extruido/hundido) **más** un segundo canal:
color de acento, icono o etiqueta. Un toggle activo es hundido *y* verde.

**DIS-04 — Foco visible siempre.** Anillo de foco de 2px en acento con offset,
visible por teclado en todos los controles. El neomorfismo no lo sustituye.

**DIS-05 — Los datos densos van en plano.** Tablas, el ledger, estados de
cuenta y listados largos usan superficie plana (sin sombras internas por fila)
*dentro de* un contenedor neomórfico. El neomorfismo enmarca; los datos se leen
en limpio. Filas alternas con cambio de tono ≤ 3%, montos alineados a la
derecha en fuente tabular.

**DIS-06 — Profundidad con presupuesto.** Máximo dos niveles de elevación por
vista: fondo → tarjeta extruida → control hundido. Prohibido anidar tres
niveles de sombras.

**DIS-07 — Débito y crédito con doble codificación.** Rojo/verde + signo +
etiqueta. Nunca solo color (daltonismo).

**DIS-08 — Movimiento reducido respetado.** Transiciones de presión (raised →
pressed) de 120–150 ms; desactivadas con `prefers-reduced-motion`.

**DIS-09 — Dinero como texto tabular.** Montos con `font-variant-numeric:
tabular-nums`, formato es-CO (`$ 1.250.000`), sin decimales visibles salvo
configuración contraria.

## 3. Tokens de diseño

### 3.1 Color

| Token | Hex | Uso |
|---|---|---|
| `surface-base` | `#E8ECF1` | Fondo global, el "material" |
| `surface-raised` | `#EDF1F6` | Tarjetas extruidas (ligeramente más clara) |
| `shadow-dark` | `#A3B1C6` @ 55% | Sombra inferior-derecha |
| `shadow-light` | `#FFFFFF` @ 90% | Luz superior-izquierda |
| `text-primary` | `#1F2430` | Texto principal |
| `text-secondary` | `#5A6478` | Texto de apoyo, labels |
| `accent` | `#047857` | Acción primaria, éxito, crédito (esmeralda — guiño colombiano) |
| `accent-soft` | `#D1E7DF` | Fondos de chips/badges de acento |
| `danger` | `#B4232C` | Débitos, mora, errores |
| `warning` | `#B45309` | Multas impuestas, alertas |

Nota: los tonos `danger` y `warning` se eligieron oscuros para cumplir DIS-01
sobre la base clara.

### 3.2 Sombras (el corazón del sistema)

```
--nm-raised:   9px 9px 18px rgba(163,177,198,.55), -9px -9px 18px rgba(255,255,255,.90);
--nm-raised-sm: 5px 5px 10px rgba(163,177,198,.50), -5px -5px 10px rgba(255,255,255,.85);
--nm-pressed:  inset 6px 6px 12px rgba(163,177,198,.55), inset -6px -6px 12px rgba(255,255,255,.90);
--nm-flat-well: inset 2px 2px 5px rgba(163,177,198,.35), inset -2px -2px 5px rgba(255,255,255,.70);
```

Uso: `raised` para tarjetas y botones en reposo; `raised-sm` para elementos
pequeños (chips, avatares); `pressed` para estado activo/presionado e inputs;
`flat-well` para el contenedor de tablas y áreas de datos (DIS-05).

### 3.3 Extensión de Tailwind (referencia para implementación)

```js
// tailwind.config.js — extend
boxShadow: {
  'nm': '9px 9px 18px rgba(163,177,198,.55), -9px -9px 18px rgba(255,255,255,.9)',
  'nm-sm': '5px 5px 10px rgba(163,177,198,.5), -5px -5px 10px rgba(255,255,255,.85)',
  'nm-in': 'inset 6px 6px 12px rgba(163,177,198,.55), inset -6px -6px 12px rgba(255,255,255,.9)',
  'nm-well': 'inset 2px 2px 5px rgba(163,177,198,.35), inset -2px -2px 5px rgba(255,255,255,.7)',
},
borderRadius: { 'nm': '1.25rem', 'nm-sm': '0.875rem' },
colors: { surface: '#E8ECF1', 'surface-raised': '#EDF1F6', accent: '#047857', /* ... */ }
```

### 3.4 Tipografía

- **Familia:** Inter (ya definida en el stack).
- **Datos numéricos:** Inter con `tabular-nums` (DIS-09).
- **Escala:** 12 / 14 / 16 / 20 / 26 / 34 px. Títulos en peso 700 con tracking
  −1%; labels en 12–13 px peso 600, mayúsculas con tracking +6%, color
  `text-secondary`.

### 3.5 Radios y espaciado

- Radio de tarjetas: 20px (`nm`); controles: 14px (`nm-sm`); botones circulares
  para acciones de icono.
- Grid de espaciado base 4px; padding interno de tarjeta 20–24px.
- El neomorfismo exige aire: densidad mínima entre tarjetas de 16px.

## 4. Anatomía de componentes clave

| Componente | Tratamiento |
|---|---|
| Tarjeta KPI (saldo de fondo) | Extruida (`nm`), label secundaria arriba, monto grande tabular, indicador de fondo (Ahorro/Rentabilidad) como chip `accent-soft` |
| Botón primario | Extruido en reposo; hundido (`nm-in`) + acento al presionar; deshabilitado = plano y 45% opacidad + cursor bloqueado |
| Input / Select | Siempre hundido (`nm-in`), label externa (nunca solo placeholder), error con borde 2px `danger` + mensaje |
| Toggle / Switch | Pista hundida; perilla extruida; activo = perilla desplazada + pista `accent` (DIS-03) |
| Tabla / Ledger | Contenedor `nm-well`, filas planas, encabezado sticky, montos tabulares derecha, débito/crédito con DIS-07 |
| Números de polla | Grid de fichas circulares extruidas; pagado = hundido con anillo `accent`; inactivo (sin pago) = plano, 40% opacidad y etiqueta "Sin pago" |
| Navegación lateral | Riel extruido; ítem activo hundido + barra de acento 3px |
| Modales | Superficie `surface-raised` con `nm`, overlay oscuro 40% (excepción justificada al monomaterial: la app financiera necesita foco total en confirmaciones) |

## 5. Modo oscuro

Fuera del MVP. El neomorfismo oscuro exige recalibrar todas las sombras
(base `#2A2D34`, luz `rgba(255,255,255,.06)`); se documentará como iteración
posterior. Los tokens ya están estructurados para soportarlo sin refactor.

## 6. Pendiente para la versión 1.0 de este documento

- Mapa de navegación y flujos por rol (bloqueado por docs 02–03).
- Wireframes de: dashboard, registro de pagos en lote, sorteo de polla,
  proceso de liquidación (wizard).
- Estados vacíos y de error con redacción definitiva.
- Definición responsive (el administrador registra pagos desde el celular:
  mobile-first en las pantallas operativas).
