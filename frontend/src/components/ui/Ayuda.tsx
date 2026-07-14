import { useEffect, useId, useRef, useState } from 'react'
import { HelpCircle, X } from 'lucide-react'
import { AYUDA, type ContenidoAyuda, type TemaAyuda } from '@/lib/ayuda'
import { cn } from '@/lib/cn'

// Ayuda contextual: un ícono ⓘ junto al título que, al hacer clic, abre un
// popover con los pasos correctos y los errores a evitar. Accesible (teclado,
// clic afuera, Esc) y compatible con móvil (no depende de hover).
export function Ayuda({ id }: { id: TemaAyuda }) {
  const info: ContenidoAyuda = AYUDA[id]
  const [abierto, setAbierto] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const panelId = useId()

  useEffect(() => {
    if (!abierto) return
    function onClickFuera(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setAbierto(false)
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === 'Escape') setAbierto(false)
    }
    document.addEventListener('mousedown', onClickFuera)
    document.addEventListener('keydown', onEsc)
    return () => {
      document.removeEventListener('mousedown', onClickFuera)
      document.removeEventListener('keydown', onEsc)
    }
  }, [abierto])

  return (
    <div className="relative inline-flex" ref={ref}>
      <button
        type="button"
        aria-label={`Ayuda: ${info.titulo}`}
        aria-expanded={abierto}
        aria-controls={panelId}
        onClick={() => setAbierto((v) => !v)}
        className={cn(
          'inline-flex h-7 w-7 items-center justify-center rounded-full transition-nm',
          abierto
            ? 'text-accent shadow-nm-in'
            : 'text-text-secondary shadow-nm-sm hover:text-accent',
        )}
      >
        <HelpCircle size={16} />
      </button>

      {abierto && (
        <div
          id={panelId}
          role="dialog"
          aria-label={info.titulo}
          className="absolute left-0 top-full z-50 mt-2 w-[min(90vw,340px)] rounded-nm bg-surface-raised p-4 text-left shadow-nm"
        >
          <div className="mb-2 flex items-start justify-between gap-2">
            <p className="font-bold tracking-tight">{info.titulo}</p>
            <button
              type="button"
              aria-label="Cerrar ayuda"
              onClick={() => setAbierto(false)}
              className="text-text-secondary transition-nm hover:text-text-primary"
            >
              <X size={16} />
            </button>
          </div>

          <p className="text-sm text-text-secondary">{info.intro}</p>

          <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-text-secondary">
            Cómo se hace
          </p>
          <ol className="mt-1.5 space-y-1.5 text-sm">
            {info.pasos.map((paso, i) => (
              <li key={paso} className="flex gap-2">
                <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full bg-accent-soft text-[11px] font-bold text-accent">
                  {i + 1}
                </span>
                <span>{paso}</span>
              </li>
            ))}
          </ol>

          {info.errores && info.errores.length > 0 && (
            <>
              <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-warning">
                Evita estos errores
              </p>
              <ul className="mt-1.5 space-y-1 text-sm text-text-secondary">
                {info.errores.map((err) => (
                  <li key={err} className="flex gap-2">
                    <span aria-hidden className="text-warning">
                      •
                    </span>
                    <span>{err}</span>
                  </li>
                ))}
              </ul>
            </>
          )}

          {info.consejo && (
            <p className="mt-3 rounded-nm-sm bg-surface p-2.5 text-xs text-text-secondary shadow-nm-in">
              💡 {info.consejo}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
