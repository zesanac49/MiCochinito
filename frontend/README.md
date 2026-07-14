# Frontend — Plataforma de Administración de Natilleras

SPA en React + TypeScript (strict) con Vite y sistema de diseño **neomórfico**
(doc 06). Consume la API del backend bajo `/api`.

## Stack (CLAUDE.md §3)

React 18.3 · TypeScript 5.7 strict · Vite 6 · react-router-dom 6 · TanStack
Query 5 · Zustand 5 · Axios (interceptor + refresh) · TailwindCSS 3.4 (Inter) ·
lucide-react.

## Estado (Sprint 2, S2-T09/T10)

- Sistema de diseño neomórfico: tokens y sombras del doc 06 §3 en
  `tailwind.config.js`; componentes base (`Card`, `Button`, `Field`, `Toggle`,
  `Tabla`, `Badge`) siguiendo DIS-01..09 (contraste WCAG, foco visible, estado
  con doble codificación, datos densos en plano, dinero tabular es-CO).
- Auth: login, tokens en `localStorage` (Zustand persist), refresh con rotación
  (interceptor Axios), rutas protegidas.
- Selector de natillera desde las membresías de `/auth/me`.
- **Participantes**: lista + alta.
- **Pagos en lote** mobile-first (≤3 interacciones, RNF-04): elegir período →
  marcar quién pagó → confirmar; el total lo devuelve la API (sin aritmética de
  dinero en el cliente, doc 08 §4).

## Comandos

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxy /api -> 127.0.0.1:8000)
npm run build      # tsc -b (strict) + vite build  -> dist/
npm run lint       # eslint, 0 warnings
npm run typecheck  # solo tipos
```

## Probar con el backend

1. Arrancar el backend en `:8000` (ver `../backend`), con la migración aplicada
   y un usuario con membresía sembrado.
2. `npm run dev` — el proxy de Vit e envía `/api` al backend.
3. Login → seleccionar natillera → participantes / pagos en lote.

En producción, el Dockerfile compila este frontend (`npm run build`) y Nginx
sirve `dist/` + proxy `/api` (doc 05 §11).

## Estructura

```
src/
  main.tsx App.tsx            # montaje + router
  lib/     api.ts formato.ts cn.ts
  store/   auth.ts            # Zustand (tokens, usuario, natillera activa)
  hooks/   auth.ts data.ts    # TanStack Query
  components/ui/              # Card, Button, Field, Toggle, Table, Badge
  components/ Layout SelectorNatillera ProtectedRoute
  pages/   Login Dashboard Participantes PagosLote
```
