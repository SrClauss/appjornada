export const ENDPOINTS = {
  auth: {
    login: '/auth/login',
    me: '/auth/me',
    registrar: '/auth/registrar',
  },
  users: {
    list: '/users',
    detail: (id: string) => `/users/${id}`,
  },
  jornadas: {
    list: '/jornadas',
  },
  veiculos: {
    list: '/veiculos/',
    detail: (placa: string) => `/veiculos/${placa}`,
  },
  manutencoes: {
    list: '/manutencoes/',
    detail: (id: string) => `/manutencoes/${id}`,
  },
  metas: {
    list: '/metas/',
    detail: (id: string) => `/metas/${id}`,
  },
  relatorios: {
    comparativo: '/relatorios/comparativo',
    importarUber: '/relatorios/importar/uber',
    importar99: '/relatorios/importar/99',
  },
}
