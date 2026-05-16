import { useState } from 'react'
import { useAuthContext } from '../../contexts/useAuthContext'

export function LoginPage() {
  const { login, isLoading } = useAuthContext()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [error, setError] = useState('')

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    try {
      await login(email, senha)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao autenticar')
    }
  }

  return (
    <main className="auth-shell">
      <form className="auth-card" onSubmit={onSubmit}>
        <h1>Painel Administrativo</h1>
        <p>Entre com seu usuário GESTOR/ADMIN.</p>

        <label>
          E-mail
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>

        <label>
          Senha
          <input type="password" value={senha} onChange={(event) => setSenha(event.target.value)} required />
        </label>

        {error ? <p className="error-text">{error}</p> : null}

        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </main>
  )
}
