import { differenceInDays, parseISO } from 'date-fns'

export function toShortDate(date?: string): string {
  if (!date) return '-'
  return new Intl.DateTimeFormat('pt-BR').format(new Date(date))
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
