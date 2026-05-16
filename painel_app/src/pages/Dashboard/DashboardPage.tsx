import { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from 'recharts'
import { format, subDays } from 'date-fns'
import { useJornadas } from '../../api/hooks/useJornadas'
import { PageHeader } from '../../components/shared/PageHeader'
import { formatCurrency, formatHoursFromSeconds } from '../../lib/utils'
import type { Jornada } from '../../types/api'

function toHourDateTime(data?: string, hour?: string): Date | null {
  if (!data || !hour) return null
  const fullHour = hour.length === 5 ? `${hour}:00` : hour
  const parsed = new Date(`${data}T${fullHour}`)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed
}

function isOpenTooLong(jornada: Jornada): boolean {
  if (!['ABERTA', 'EM_ANDAMENTO'].includes(jornada.status)) return false
  const start = toHourDateTime(jornada.data, jornada.horario?.inicio)
  if (!start) return false
  const diffHours = (Date.now() - start.getTime()) / 3_600_000
  return diffHours > 12
}

function isPauseTooLong(jornada: Jornada): boolean {
  if (jornada.status !== 'EM_PAUSA') return false
  const lastPause = jornada.pausas?.[jornada.pausas.length - 1]
  const start = toHourDateTime(jornada.data, lastPause?.inicio)
  if (!start) return false
  const diffHours = (Date.now() - start.getTime()) / 3_600_000
  return diffHours > 2
}

function isClosedWithoutRevenue(jornada: Jornada): boolean {
  return jornada.status === 'ENCERRADA' && (jornada.faturamento?.total_dia ?? 0) === 0
}

export function DashboardPage() {
  const today = format(new Date(), 'yyyy-MM-dd')
  const sevenDaysAgo = format(subDays(new Date(), 6), 'yyyy-MM-dd')

  const todayQuery = useJornadas({ data: today, limit: 200 })
  const weekQuery = useJornadas({ limit: 200 })

  const todayJornadas = useMemo(() => todayQuery.data ?? [], [todayQuery.data])
  const weekJornadas = useMemo(
    () => (weekQuery.data ?? []).filter((j) => (j.data ?? '') >= sevenDaysAgo),
    [weekQuery.data, sevenDaysAgo],
  )

  const kpis = useMemo(() => {
    const activeDrivers = new Set(
      todayJornadas
        .filter((jornada) => ['ABERTA', 'EM_ANDAMENTO'].includes(jornada.status))
        .map((jornada) => jornada.motorista_id),
    ).size

    const kmDia = todayJornadas.reduce((sum, jornada) => sum + (jornada.km?.rodados ?? 0), 0)
    const faturamentoDia = todayJornadas.reduce((sum, jornada) => sum + (jornada.faturamento?.total_dia ?? 0), 0)

    const alerts = todayJornadas.filter(
      (jornada) => isOpenTooLong(jornada) || isPauseTooLong(jornada) || isClosedWithoutRevenue(jornada),
    ).length

    return { activeDrivers, kmDia, faturamentoDia, alerts }
  }, [todayJornadas])

  const barData = useMemo(() => {
    const grouped = new Map<string, number>()
    weekJornadas.forEach((jornada) => {
      const key = jornada.data ?? 'Sem data'
      grouped.set(key, (grouped.get(key) ?? 0) + (jornada.faturamento?.total_dia ?? 0))
    })
    return Array.from(grouped.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([data, faturamento]) => ({ data, faturamento }))
  }, [weekJornadas])

  const lineData = useMemo(() => {
    const grouped = new Map<string, number>()
    weekJornadas.forEach((jornada) => {
      grouped.set(
        jornada.motorista_id,
        (grouped.get(jornada.motorista_id) ?? 0) + (jornada.horario?.total_horas_segundos ?? 0),
      )
    })

    return Array.from(grouped.entries()).map(([motoristaId, segundos]) => ({
      motoristaId: motoristaId.slice(-6),
      horas: Number((segundos / 3600).toFixed(1)),
      meta: 220,
    }))
  }, [weekJornadas])

  const pieData = useMemo(() => {
    const statusCount = todayJornadas.reduce<Record<string, number>>((acc, jornada) => {
      acc[jornada.status] = (acc[jornada.status] ?? 0) + 1
      return acc
    }, {})

    return Object.entries(statusCount).map(([status, value]) => ({ status, value }))
  }, [todayJornadas])

  const alertsRows = todayJornadas.filter(
    (jornada) => isOpenTooLong(jornada) || isPauseTooLong(jornada) || isClosedWithoutRevenue(jornada),
  )

  const isLoading = todayQuery.isLoading || weekQuery.isLoading
  const hasError = todayQuery.isError || weekQuery.isError

  return (
    <section>
      <PageHeader title="Dashboard" subtitle="Visão geral da operação diária" />

      {isLoading ? <p className="empty-state">Carregando dados...</p> : null}
      {hasError ? <p className="error-text">Falha ao carregar dados do dashboard.</p> : null}

      {!isLoading && !hasError ? (
        <>
          <div className="kpi-grid">
            <article className="card"><h3>Motoristas ativos</h3><strong>{kpis.activeDrivers}</strong></article>
            <article className="card"><h3>KM total do dia</h3><strong>{kpis.kmDia.toFixed(1)} km</strong></article>
            <article className="card"><h3>Faturamento do dia</h3><strong>{formatCurrency(kpis.faturamentoDia)}</strong></article>
            <article className="card"><h3>Alertas</h3><strong>{kpis.alerts}</strong></article>
          </div>

          <div className="chart-grid">
            <article className="card chart-card">
              <h3>Faturamento diário (7 dias)</h3>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="data" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="faturamento" fill="#2563eb" />
                </BarChart>
              </ResponsiveContainer>
            </article>

            <article className="card chart-card">
              <h3>Horas acumuladas vs meta CLT</h3>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={lineData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="motoristaId" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line dataKey="horas" stroke="#16a34a" />
                  <Line dataKey="meta" stroke="#dc2626" strokeDasharray="5 5" />
                </LineChart>
              </ResponsiveContainer>
            </article>

            <article className="card chart-card">
              <h3>Status das jornadas do dia</h3>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="status" outerRadius={90}>
                    {pieData.map((entry, index) => (
                      <Cell
                        key={entry.status}
                        fill={['#2563eb', '#16a34a', '#d97706', '#7c3aed'][index % 4]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </article>
          </div>

          <article className="card">
            <h3>Tabela de alertas</h3>
            {alertsRows.length === 0 ? <p className="empty-state">Sem alertas no momento.</p> : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Jornada</th>
                    <th>Status</th>
                    <th>Motivo</th>
                    <th>Horas trabalhadas</th>
                  </tr>
                </thead>
                <tbody>
                  {alertsRows.map((jornada) => {
                    let motivo = 'Alerta operacional'
                    if (isOpenTooLong(jornada)) motivo = 'Jornada aberta há mais de 12h'
                    if (isPauseTooLong(jornada)) motivo = 'Pausa em aberto há mais de 2h'
                    if (isClosedWithoutRevenue(jornada)) motivo = 'Jornada encerrada sem faturamento'

                    return (
                      <tr key={jornada.id}>
                        <td>{jornada.id}</td>
                        <td>{jornada.status}</td>
                        <td>{motivo}</td>
                        <td>{formatHoursFromSeconds(jornada.horario?.total_horas_segundos)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </article>
        </>
      ) : null}
    </section>
  )
}
