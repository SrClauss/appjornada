export const TOKEN_KEY = 'token'

export function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
}

export function formatCurrency(value?: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value ?? 0)
}

export function formatHoursFromSeconds(totalSeconds?: number): string {
  if (!totalSeconds || totalSeconds <= 0) return '0h'
  const hours = totalSeconds / 3600
  return `${hours.toFixed(1)}h`
}
