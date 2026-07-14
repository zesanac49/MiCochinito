import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  /** DIS-02: una sola acción primaria (acento) visible por vista. */
  variante?: 'primaria' | 'neutra' | 'peligro'
  cargando?: boolean
}

export function Button({
  children,
  variante = 'neutra',
  cargando,
  disabled,
  className,
  ...rest
}: ButtonProps) {
  const bloqueado = disabled || cargando
  return (
    <button
      disabled={bloqueado}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-nm-sm px-5 py-2.5',
        'text-sm font-semibold transition-nm active:shadow-nm-in',
        bloqueado
          ? 'cursor-not-allowed opacity-45 shadow-none'
          : 'shadow-nm-sm hover:brightness-[1.02]',
        variante === 'primaria' && 'bg-accent-soft text-accent active:text-accent',
        variante === 'peligro' && 'text-danger',
        variante === 'neutra' && 'text-text-primary',
        className,
      )}
      {...rest}
    >
      {cargando && (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  )
}
