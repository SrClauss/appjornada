import { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useJornadas } from '../../api/hooks/useJornadas'
import { useMotoristas } from '../../api/hooks/useMotoristas'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageHeader } from '../../components/shared/PageHeader'
import { toShortDate, toShortTime } from '../../lib/formatters'
import { formatCurrency, formatHoursFromSeconds } from '../../lib/utils'
import type { Abastecimento, Jornada, Pausa } from '../../types/api'

function statusTone(status?: string): 'blue' | 'green' | 'yellow' | 'purple' | 'gray' {
  if (status === 'ENCERRADA') return 'green'
  if (status === 'EM_PAUSA') return 'yellow'
  if (status === 'EM_ANDAMENTO') return 'blue'
  if (status === 'ABERTA') return 'purple'
  return 'gray'
}

function inDateRange(date: string | undefined, startDate: string, endDate: string) {
  if (!date) return false
  if (startDate && date < startDate) return false
  if (endDate && date > endDate) return false
  return true
}

function totalAbastecimento(abastecimento: Abastecimento) {
  return (abastecimento.valor_gnv ?? 0) + (abastecimento.valor_gasolina ?? 0) + (abastecimento.valor_etanol ?? 0)
}

function saldoHorasLabel(value?: number) {
  if (value == null) return '-'
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}h`
}

function duracaoPausa(pausa: Pausa) {
  return formatHoursFromSeconds(pausa.duracao_segundos)
}

function JornadaDialog({
  jornada,
  motoristaNome,
  onClose,
}: {
  jornada: Jornada
  motoristaNome: string
  onClose: () => void
}) {
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal-card modal-large">
        <header className="modal-header">
          <div>
            <h3>Detalhes da jornada</h3>
            <p>{jornada.id}</p>
          </div>
          <button type="button" className="secondary-button" onClick={onClose}>Fechar</button>
        </header>

        <div className="detail-grid">
          <section className="detail-section">
            <h4>Cabeçalho</h4>
            <div className="detail-list">
              <div><span>Data</span><strong>{toShortDate(jornada.data)}</strong></div>
              <div><span>Motorista</span><strong>{motoristaNome}</strong></div>
              <div><span>Veículo</span><strong>{jornada.veiculo_id}</strong></div>
              <div>
                <span>Status</span>
                <StatusBadge label={jornada.status} tone={statusTone(jornada.status)} />
              </div>
            </div>
          </section>

          <section className="detail-section">
            <h4>Horários</h4>
            <div className="detail-list">
              <div><span>Início</span><strong>{toShortTime(jornada.horario?.inicio)}</strong></div>
              <div><span>Fim</span><strong>{toShortTime(jornada.horario?.fim)}</strong></div>
              <div><span>Duração total</span><strong>{formatHoursFromSeconds(jornada.horario?.total_horas_segundos)}</strong></div>
              <div><span>Saldo CLT</span><strong>{saldoHorasLabel(jornada.saldo_horas_dia)}</strong></div>
            </div>
          </section>

          <section className="detail-section">
            <h4>Quilometragem</h4>
            <div className="detail-list">
              <div><span>KM inicial</span><strong>{jornada.km?.inicial ?? '-'}</strong></div>
              <div><span>KM final</span><strong>{jornada.km?.final ?? '-'}</strong></div>
              <div><span>KM rodados</span><strong>{jornada.km?.rodados ?? '-'}</strong></div>
              <div><span>KM morta</span><strong>{jornada.km?.morta ?? '-'}</strong></div>
            </div>
          </section>

          <section className="detail-section">
            <h4>Faturamento</h4>
            <div className="detail-list">
              <div><span>Uber</span><strong>{formatCurrency(jornada.faturamento?.uber)}</strong></div>
              <div><span>99</span><strong>{formatCurrency(jornada.faturamento?.noventa_nove)}</strong></div>
              <div><span>Outros</span><strong>{formatCurrency(jornada.faturamento?.outros)}</strong></div>
              <div><span>Total</span><strong>{formatCurrency(jornada.faturamento?.total_dia)}</strong></div>
            </div>
            <div className="link-list">
              {jornada.faturamento?.comprovante_uber_url ? <a href={jornada.faturamento.comprovante_uber_url} target="_blank" rel="noreferrer">Comprovante Uber</a> : null}
              {jornada.faturamento?.comprovante_99_url ? <a href={jornada.faturamento.comprovante_99_url} target="_blank" rel="noreferrer">Comprovante 99</a> : null}
              {jornada.faturamento?.comprovante_outros_url ? <a href={jornada.faturamento.comprovante_outros_url} target="_blank" rel="noreferrer">Comprovante Outros</a> : null}
            </div>
          </section>

          <section className="detail-section">
            <h4>Pausas</h4>
            {jornada.pausas?.length ? (
              <ul className="timeline-list">
                {jornada.pausas.map((pausa) => (
                  <li key={pausa.id}>
                    <strong>{pausa.tipo ?? 'Pausa'}</strong>
                    <span>{toShortTime(pausa.inicio)} → {toShortTime(pausa.fim)}</span>
                    <span>{duracaoPausa(pausa)}</span>
                  </li>
                ))}
              </ul>
            ) : <p className="empty-state">Sem pausas registradas.</p>}
          </section>

          <section className="detail-section">
            <h4>Abastecimentos</h4>
            {jornada.abastecimentos?.length ? (
              <table className="table compact-table">
                <thead>
                  <tr>
                    <th>KM</th>
                    <th>Valores</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {jornada.abastecimentos.map((abastecimento) => (
                    <tr key={abastecimento.id}>
                      <td>{abastecimento.km ?? '-'}</td>
                      <td>
                        GNV {formatCurrency(abastecimento.valor_gnv)}<br />
                        Gasolina {formatCurrency(abastecimento.valor_gasolina)}<br />
                        Etanol {formatCurrency(abastecimento.valor_etanol)}
                      </td>
                      <td>{formatCurrency(totalAbastecimento(abastecimento))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <p className="empty-state">Sem abastecimentos.</p>}
          </section>

          <section className="detail-section">
            <h4>GPS</h4>
            <div className="detail-list">
              <div>
                <span>Inicial</span>
                <strong>{jornada.localizacao_inicial ? `${jornada.localizacao_inicial.lat}, ${jornada.localizacao_inicial.lon}` : '-'}</strong>
              </div>
              <div>
                <span>Final</span>
                <strong>{jornada.localizacao_final ? `${jornada.localizacao_final.lat}, ${jornada.localizacao_final.lon}` : '-'}</strong>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

export function JornadasPage() {
  const jornadasQuery = useJornadas({ limit: 200 })
  const motoristasQuery = useMotoristas()
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [motoristaId, setMotoristaId] = useState('')
  const [statusFiltro, setStatusFiltro] = useState('')
  const [selectedJornada, setSelectedJornada] = useState<Jornada | null>(null)

  const motoristas = useMemo(() => motoristasQuery.data ?? [], [motoristasQuery.data])
  const motoristasById = useMemo(
    () => motoristas.reduce<Record<string, string>>((acc, motorista) => {
      acc[motorista.id] = motorista.nome
      return acc
    }, {}),
    [motoristas],
  )

  const filteredJornadas = useMemo(() => {
    const jornadas = jornadasQuery.data ?? []
    return [...jornadas]
      .filter((jornada) => inDateRange(jornada.data, startDate, endDate))
      .filter((jornada) => (motoristaId ? jornada.motorista_id === motoristaId : true))
      .filter((jornada) => (statusFiltro ? jornada.status === statusFiltro : true))
      .sort((a, b) => `${b.data ?? ''}${b.horario?.inicio ?? ''}`.localeCompare(`${a.data ?? ''}${a.horario?.inicio ?? ''}`))
  }, [endDate, jornadasQuery.data, motoristaId, startDate, statusFiltro])

  const chartData = useMemo(() => {
    const grouped = new Map<string, number>()
    filteredJornadas.forEach((jornada) => {
      const key = jornada.data ?? 'Sem data'
      grouped.set(key, (grouped.get(key) ?? 0) + (jornada.km?.rodados ?? 0))
    })
    return Array.from(grouped.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([data, km]) => ({ data, km: Number(km.toFixed(1)) }))
  }, [filteredJornadas])

  const isLoading = jornadasQuery.isLoading || motoristasQuery.isLoading
  const hasError = jornadasQuery.isError || motoristasQuery.isError

  return (
    <section>
      <PageHeader title="Jornadas" subtitle="Listagem filtrada com detalhamento operacional" />

      <article className="card">
        <div className="filters">
          <label>
            <span>Data inicial</span>
            <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          </label>
          <label>
            <span>Data final</span>
            <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
          </label>
          <label>
            <span>Motorista</span>
            <select value={motoristaId} onChange={(event) => setMotoristaId(event.target.value)}>
              <option value="">Todos</option>
              {motoristas.map((motorista) => (
                <option key={motorista.id} value={motorista.id}>{motorista.nome}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Status</span>
            <select value={statusFiltro} onChange={(event) => setStatusFiltro(event.target.value)}>
              <option value="">Todos</option>
              <option value="ABERTA">ABERTA</option>
              <option value="EM_ANDAMENTO">EM_ANDAMENTO</option>
              <option value="EM_PAUSA">EM_PAUSA</option>
              <option value="ENCERRADA">ENCERRADA</option>
            </select>
          </label>
        </div>
      </article>

      {isLoading ? <p className="empty-state">Carregando jornadas...</p> : null}
      {hasError ? <p className="error-text">Falha ao carregar jornadas.</p> : null}

      {!isLoading && !hasError ? (
        <>
          <article className="card chart-card">
            <div className="section-header">
              <div>
                <h3>KM rodados por jornada</h3>
                <p>{filteredJornadas.length} jornada(s) no filtro atual</p>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="data" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="km" fill="#2563eb" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </article>

          <article className="card">
            <h3>Jornadas filtradas</h3>
            {filteredJornadas.length === 0 ? <p className="empty-state">Nenhuma jornada encontrada.</p> : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Data</th>
                    <th>Motorista</th>
                    <th>Veículo</th>
                    <th>Status</th>
                    <th>KM</th>
                    <th>Faturamento</th>
                    <th>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredJornadas.map((jornada) => (
                    <tr key={jornada.id}>
                      <td>{toShortDate(jornada.data)}</td>
                      <td>{motoristasById[jornada.motorista_id] ?? jornada.motorista_id}</td>
                      <td>{jornada.veiculo_id}</td>
                      <td><StatusBadge label={jornada.status} tone={statusTone(jornada.status)} /></td>
                      <td>{jornada.km?.rodados?.toFixed(1) ?? '-'} km</td>
                      <td>{formatCurrency(jornada.faturamento?.total_dia)}</td>
                      <td>
                        <button type="button" className="secondary-button" onClick={() => setSelectedJornada(jornada)}>
                          Ver detalhes
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </article>
        </>
      ) : null}

      {selectedJornada ? (
        <JornadaDialog
          jornada={selectedJornada}
          motoristaNome={motoristasById[selectedJornada.motorista_id] ?? selectedJornada.motorista_id}
          onClose={() => setSelectedJornada(null)}
        />
      ) : null}
    </section>
  )
}
