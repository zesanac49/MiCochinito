import { cn } from '@/lib/cn'

interface ToggleProps {
  activo: boolean
  onChange: (v: boolean) => void
  etiqueta: string
}

// Interruptor: pista hundida, perilla extruida; activo = perilla desplazada +
// pista acento (DIS-03: estado nunca depende solo de la sombra).
export function Toggle({ activo, onChange, etiqueta }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={activo}
      aria-label={etiqueta}
      onClick={() => onChange(!activo)}
      className={cn(
        'relative h-7 w-12 shrink-0 rounded-full shadow-nm-in transition-nm',
        activo ? 'bg-accent' : 'bg-surface',
      )}
    >
      <span
        className={cn(
          'absolute top-0.5 h-6 w-6 rounded-full bg-surface-raised shadow-nm-sm transition-nm',
          activo ? 'left-[22px]' : 'left-0.5',
        )}
      />
    </button>
  )
}
