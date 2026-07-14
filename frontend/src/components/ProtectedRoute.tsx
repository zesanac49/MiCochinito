import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/store/auth'

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const access = useAuth((s) => s.access)
  if (!access) return <Navigate to="/login" replace />
  return <>{children}</>
}
