// Une clases condicionales sin dependencias externas.
export function cn(...partes: Array<string | false | null | undefined>): string {
  return partes.filter(Boolean).join(' ')
}
