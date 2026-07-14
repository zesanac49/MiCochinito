import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface CardProps {
  children: ReactNode
  className?: string
  /** Contenedor plano para datos densos (tablas, ledger): DIS-05. */
  well?: boolean
}

// Tarjeta extruida (DIS-06: máx. dos niveles de elevación por vista).
export function Card({ children, className, well }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-nm bg-surface-raised p-6',
        well ? 'shadow-nm-well' : 'shadow-nm',
        className,
      )}
    >
      {children}
    </div>
  )
}

export function CardTitulo({ children }: { children: ReactNode }) {
  return (
    <h2 className="mb-4 text-[13px] font-semibold uppercase tracking-[0.06em] text-text-secondary">
      {children}
    </h2>
  )
}
