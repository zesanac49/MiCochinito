import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

// Input siempre hundido (nm-in), label externa (nunca solo placeholder), error
// con borde danger + mensaje (doc 06 §4).

const baseCampo =
  'w-full rounded-nm-sm bg-surface px-4 py-2.5 text-sm text-text-primary ' +
  'shadow-nm-in placeholder:text-text-secondary/60 focus:outline-none'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
}

export function Field({ label, error, className, id, ...rest }: FieldProps) {
  const campoId = id ?? rest.name
  return (
    <label className="block" htmlFor={campoId}>
      <Etiqueta>{label}</Etiqueta>
      <input
        id={campoId}
        className={cn(baseCampo, error && 'ring-2 ring-danger', className)}
        {...rest}
      />
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </label>
  )
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  children: ReactNode
}

export function SelectField({ label, children, className, id, ...rest }: SelectFieldProps) {
  const campoId = id ?? rest.name
  return (
    <label className="block" htmlFor={campoId}>
      <Etiqueta>{label}</Etiqueta>
      <select id={campoId} className={cn(baseCampo, className)} {...rest}>
        {children}
      </select>
    </label>
  )
}

function Etiqueta({ children }: { children: ReactNode }) {
  return (
    <span className="mb-1.5 block text-[12px] font-semibold uppercase tracking-[0.06em] text-text-secondary">
      {children}
    </span>
  )
}
