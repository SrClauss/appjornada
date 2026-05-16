import { differenceInDays, format, parseISO } from 'date-fns'

export function toShortDate(date?: string): string {
  if (!date) return '-'
  return format(parseISO(date), 'dd/MM/yyyy')
}

export function toShortDateTime(value?: string): string {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(parsed)
}

export function toShortTime(value?: string): string {
  if (!value) return '-'
  const clean = value.slice(0, 8)
  return clean || '-'
}

export function cnhStatus(vencimento?: string): 'VALIDA' | 'ATENCAO' | 'EXPIRADA' | 'SEM_DADO' {
  if (!vencimento) return 'SEM_DADO'
  const days = differenceInDays(parseISO(vencimento), new Date())
  if (days < 0) return 'EXPIRADA'
  if (days < 30) return 'EXPIRADA'
  if (days <= 60) return 'ATENCAO'
  return 'VALIDA'
}

export function cnhStatusLabel(status: ReturnType<typeof cnhStatus>): string {
  if (status === 'VALIDA') return 'Válida'
  if (status === 'ATENCAO') return 'Atenção'
  if (status === 'EXPIRADA') return 'Expirada'
  return 'Sem dado'
}
