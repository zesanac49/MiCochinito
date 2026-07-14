import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

// Datos densos en plano dentro de un contenedor neomórfico (DIS-05).
export function Tabla({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-nm bg-surface p-2 shadow-nm-well">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  )
}

export function Th({ children, right }: { children: ReactNode; right?: boolean }) {
  return (
    <th
      className={cn(
        'sticky top-0 bg-surface px-3 py-2.5 text-[12px] font-semibold uppercase',
        'tracking-[0.05em] text-text-secondary',
        right ? 'text-right' : 'text-left',
      )}
    >
      {children}
    </th>
  )
}

export function Td({
  children,
  right,
  tabular,
}: {
  children: ReactNode
  right?: boolean
  tabular?: boolean
}) {
  return (
    <td
      className={cn(
        'px-3 py-2.5 text-text-primary',
        right && 'text-right',
        tabular && 'tabular',
      )}
    >
      {children}
    </td>
  )
}

export function Tr({ children }: { children: ReactNode }) {
  // Filas alternas con cambio de tono ≤3% (DIS-05).
  return <tr className="odd:bg-white/30">{children}</tr>
}
