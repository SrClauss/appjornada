import axios, { AxiosError } from 'axios'
import { TOKEN_KEY, getApiBaseUrl } from '../lib/utils'

const statusMessages: Record<number, string> = {
  400: 'Requisição inválida.',
  401: 'Sessão expirada. Faça login novamente.',
  403: 'Você não possui permissão para esta ação.',
  404: 'Recurso não encontrado.',
  409: 'Conflito de dados.',
  422: 'Dados inválidos.',
  500: 'Erro interno do servidor.',
}

export const api = axios.create({
  baseURL: getApiBaseUrl(),
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const status = error.response?.status
    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }

    const detail = error.response?.data?.detail
    const mapped = status ? statusMessages[status] : undefined
    const message = detail || mapped || 'Falha de comunicação com a API.'

    return Promise.reject(new Error(message))
  },
)
