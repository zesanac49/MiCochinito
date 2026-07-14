import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { Actividades } from '@/pages/Actividades'
import { ActividadDetalle } from '@/pages/ActividadDetalle'
import { Dashboard } from '@/pages/Dashboard'
import { Liquidacion } from '@/pages/Liquidacion'
import { Login } from '@/pages/Login'
import { Multas } from '@/pages/Multas'
import { Natillera } from '@/pages/Natillera'
import { PagosLote } from '@/pages/PagosLote'
import { ParticipanteDetalle } from '@/pages/ParticipanteDetalle'
import { Participantes } from '@/pages/Participantes'
import { Prestamos } from '@/pages/Prestamos'
import { Reportes } from '@/pages/Reportes'
import { Usuarios } from '@/pages/Usuarios'

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/natillera" element={<Natillera />} />
        <Route path="/participantes" element={<Participantes />} />
        <Route path="/participantes/:uuid" element={<ParticipanteDetalle />} />
        <Route path="/pagos" element={<PagosLote />} />
        <Route path="/prestamos" element={<Prestamos />} />
        <Route path="/multas" element={<Multas />} />
        <Route path="/actividades" element={<Actividades />} />
        <Route path="/actividades/:uuid" element={<ActividadDetalle />} />
        <Route path="/reportes" element={<Reportes />} />
        <Route path="/usuarios" element={<Usuarios />} />
        <Route path="/liquidacion" element={<Liquidacion />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
