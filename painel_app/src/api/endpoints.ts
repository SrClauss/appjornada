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
}
