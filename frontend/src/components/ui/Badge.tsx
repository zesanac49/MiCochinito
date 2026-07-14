import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

type Tono = 'acento' | 'neutro' | 'peligro' | 'alerta'

// Estado con doble codificación (DIS-03/07): color + etiqueta, nunca solo color.
export function Badge({ children, tono = 'neutro' }: { children: ReactNode; tono?: Tono }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
        tono === 'acento' && 'bg-accent-soft text-accent',
        tono === 'neutro' && 'bg-surface text-text-secondary shadow-nm-sm',
        tono === 'peligro' && 'bg-danger/10 text-danger',
        tono === 'alerta' && 'bg-warning/10 text-warning',
      )}
    >
      {children}
    </span>
  )
}
