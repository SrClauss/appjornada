import { useMemo, useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useJornadas } from '../../api/hooks/useJornadas'
import { useCreateMotorista, useMotoristas, useUpdateMotorista } from '../../api/hooks/useMotoristas'
import { DataTable } from '../../components/shared/DataTable'
import { PageHeader } from '../../components/shared/PageHeader'
import { cnhStatus, cnhStatusLabel, toShortDate } from '../../lib/formatters'
import { formatCurrency, formatHoursFromSeconds } from '../../lib/utils'
import type { Jornada, UserPublic } from '../../types/api'

const createMotoristaSchema = z.object({
  nome: z.string().min(3, 'Informe o nome'),
  email: z.string().email('E-mail inválido'),
  senha: z.string().min(4, 'Mínimo 4 caracteres'),
  cpf: z.string().min(11, 'CPF inválido'),
  telefone: z.string().min(8, 'Telefone inválido'),
  cnhVencimento: z.string().min(10, 'Informe o vencimento da CNH'),
})

type CreateMotoristaForm = z.infer<typeof createMotoristaSchema>

function sumHours(jornadas: Jornada[]): number {
  return jornadas.reduce((acc, item) => acc + (item.horario?.total_horas_segundos ?? 0), 0)
}

function sumBonus(jornadas: Jornada[]): number {
  return jornadas.reduce((acc, item) => acc + (item.bonus_acumulado_mes ?? 0), 0)
}

function DriverSheet({ driver, onClose }: { driver: UserPublic; onClose: () => void }) {
  const [tab, setTab] = useState<'dados' | 'cnh' | 'bancarios' | 'clt' | 'historico' | 'bonus'>('dados')
  const [nome, setNome] = useState(driver.nome)
  const [cpf, setCpf] = useState(driver.perfil_motorista?.cpf ?? '')
  const [telefone, setTelefone] = useState(driver.perfil_motorista?.telefone ?? '')
  const [cnhVencimento, setCnhVencimento] = useState(driver.perfil_motorista?.cnh?.vencimento ?? '')
  const updateMutation = useUpdateMotorista(driver.id)
  const jornadasQuery = useJornadas({ motorista_id: driver.id, limit: 10 })

  async function onSave() {
    await updateMutation.mutateAsync({ nome, cpf, telefone, cnhVencimento })
  }

  const jornadas = jornadasQuery.data ?? []
  const totalHoras = sumHours(jornadas)
  const progress = Math.min((totalHoras / (220 * 3600)) * 100, 100)
  const bonus = sumBonus(jornadas)
  const cnh = cnhStatus(cnhVencimento)

  return (
    <div className="sheet-overlay" role="dialog" aria-modal="true">
      <aside className="sheet">
        <header>
          <h3>{driver.nome}</h3>
          <button type="button" onClick={onClose}>Fechar</button>
        </header>

        <nav className="sheet-tabs">
          {[
            ['dados', 'Dados Pessoais'],
            ['cnh', 'CNH'],
            ['bancarios', 'Dados Bancários'],
            ['clt', 'Horas CLT'],
            ['historico', 'Histórico'],
            ['bonus', 'Bônus'],
          ].map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={tab === value ? 'active' : ''}
              onClick={() => setTab(value as typeof tab)}
            >
              {label}
            </button>
          ))}
        </nav>

        {tab === 'dados' ? (
          <section className="sheet-content">
            <label>Nome <input value={nome} onChange={(event) => setNome(event.target.value)} /></label>
            <label>CPF <input value={cpf} onChange={(event) => setCpf(event.target.value)} /></label>
            <label>Telefone <input value={telefone} onChange={(event) => setTelefone(event.target.value)} /></label>
            <button type="button" onClick={onSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Salvando...' : 'Salvar dados'}
            </button>
          </section>
        ) : null}

        {tab === 'cnh' ? (
          <section className="sheet-content">
            <p>Status: <strong>{cnhStatusLabel(cnh)}</strong></p>
            <label>
              Vencimento
              <input type="date" value={cnhVencimento} onChange={(event) => setCnhVencimento(event.target.value)} />
            </label>
          </section>
        ) : null}

        {tab === 'bancarios' ? (
          <section className="sheet-content">
            <p>Banco: {driver.perfil_motorista?.dados_bancarios?.banco ?? '-'}</p>
            <p>Agência: {driver.perfil_motorista?.dados_bancarios?.agencia ?? '-'}</p>
            <p>Conta: {driver.perfil_motorista?.dados_bancarios?.conta ?? '-'}</p>
            <p>CNPJ: {driver.perfil_motorista?.dados_bancarios?.cnpj ?? '-'}</p>
          </section>
        ) : null}

        {tab === 'clt' ? (
          <section className="sheet-content">
            <p>Total no mês: {formatHoursFromSeconds(totalHoras)}</p>
            <div className="progress-bar"><div style={{ width: `${progress}%` }} /></div>
          </section>
        ) : null}

        {tab === 'historico' ? (
          <section className="sheet-content">
            {jornadas.length === 0 ? <p className="empty-state">Sem jornadas.</p> : (
              <ul className="compact-list">
                {jornadas.map((jornada) => (
                  <li key={jornada.id}>
                    <strong>{toShortDate(jornada.data)}</strong> — {jornada.status} — {formatCurrency(jornada.faturamento?.total_dia)}
                  </li>
                ))}
              </ul>
            )}
          </section>
        ) : null}

        {tab === 'bonus' ? (
          <section className="sheet-content">
            <p>Bônus acumulado (últimas jornadas): <strong>{formatCurrency(bonus)}</strong></p>
          </section>
        ) : null}
      </aside>
    </div>
  )
}

export function MotoristasPage() {
  const query = useMotoristas()
  const allJornadasQuery = useJornadas({ limit: 200 })
  const createMutation = useCreateMotorista()
  const [busca, setBusca] = useState('')
  const [filtroCnh, setFiltroCnh] = useState<'TODOS' | 'VALIDA' | 'ATENCAO' | 'EXPIRADA'>('TODOS')
  const [selectedDriver, setSelectedDriver] = useState<UserPublic | null>(null)

  const form = useForm<CreateMotoristaForm>({
    resolver: zodResolver(createMotoristaSchema),
    defaultValues: {
      nome: '',
      email: '',
      senha: '',
      cpf: '',
      telefone: '',
      cnhVencimento: '',
    },
  })

  const drivers = useMemo(() => query.data ?? [], [query.data])
  const filteredDrivers = useMemo(() => {
    return drivers.filter((driver) => {
      const textMatch = driver.nome.toLowerCase().includes(busca.toLowerCase())
      const status = cnhStatus(driver.perfil_motorista?.cnh?.vencimento)
      const cnhMatch = filtroCnh === 'TODOS' ? true : filtroCnh === status
      return textMatch && cnhMatch
    })
  }, [busca, drivers, filtroCnh])

  const hoursByDriver = useMemo(() => {
    const allJornadas = allJornadasQuery.data ?? []
    return filteredDrivers.reduce<Record<string, number>>((acc, driver) => {
      const jornadas = allJornadas.filter((jornada) => jornada.motorista_id === driver.id)
      acc[driver.id] = sumHours(jornadas)
      return acc
    }, {})
  }, [allJornadasQuery.data, filteredDrivers])

  async function onSubmit(values: CreateMotoristaForm) {
    await createMutation.mutateAsync(values)
    form.reset()
  }

  return (
    <section>
      <PageHeader title="Gestão de Motoristas" subtitle="Cadastro, filtros e visão detalhada" />

      <article className="card">
        <h3>Novo motorista</h3>
        <form className="inline-form" onSubmit={form.handleSubmit(onSubmit)}>
          <input placeholder="Nome" {...form.register('nome')} />
          <input placeholder="E-mail" {...form.register('email')} />
          <input type="password" placeholder="Senha" {...form.register('senha')} />
          <input placeholder="CPF" {...form.register('cpf')} />
          <input placeholder="Telefone" {...form.register('telefone')} />
          <input type="date" {...form.register('cnhVencimento')} />
          <button type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? 'Cadastrando...' : 'Cadastrar'}
          </button>
        </form>
        {Object.values(form.formState.errors).length > 0 ? (
          <p className="error-text">Revise os campos obrigatórios do cadastro.</p>
        ) : null}
      </article>

      <article className="card">
        <h3>Motoristas</h3>
        <div className="filters">
          <input placeholder="Buscar por nome" value={busca} onChange={(event) => setBusca(event.target.value)} />
          <select value={filtroCnh} onChange={(event) => setFiltroCnh(event.target.value as typeof filtroCnh)}>
            <option value="TODOS">Todas as CNHs</option>
            <option value="VALIDA">Válida</option>
            <option value="ATENCAO">Atenção</option>
            <option value="EXPIRADA">Expirada</option>
          </select>
        </div>

        {query.isLoading ? <p className="empty-state">Carregando motoristas...</p> : null}
        {query.isError ? <p className="error-text">Falha ao carregar motoristas.</p> : null}

        {!query.isLoading && !query.isError ? (
          <DataTable
            columns={['Nome', 'E-mail', 'Status CNH', 'Horas no mês', 'Ações']}
            rows={filteredDrivers}
            emptyText="Nenhum motorista encontrado"
            renderRow={(driver) => (
              <tr key={driver.id}>
                <td>{driver.nome}</td>
                <td>{driver.email}</td>
                <td>{cnhStatusLabel(cnhStatus(driver.perfil_motorista?.cnh?.vencimento))}</td>
                <td>{formatHoursFromSeconds(hoursByDriver[driver.id])}</td>
                <td>
                  <button type="button" onClick={() => setSelectedDriver(driver)}>Ver detalhes</button>
                </td>
              </tr>
            )}
          />
        ) : null}
      </article>

      {selectedDriver ? <DriverSheet driver={selectedDriver} onClose={() => setSelectedDriver(null)} /> : null}
    </section>
  )
}
