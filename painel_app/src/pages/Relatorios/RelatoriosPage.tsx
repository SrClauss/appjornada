import { useMemo, useState, type ChangeEvent, type DragEvent } from 'react'
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { useJornadas } from '../../api/hooks/useJornadas'
import { useMetas } from '../../api/hooks/useMetas'
import { useMotoristas } from '../../api/hooks/useMotoristas'
import { useComparativoRelatorio, useImportRelatorio, type PlataformaRelatorio } from '../../api/hooks/useRelatorios'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageHeader } from '../../components/shared/PageHeader'
import { toShortDate } from '../../lib/formatters'
import { formatCurrency, formatHoursFromSeconds } from '../../lib/utils'
import type { ComparativoMotorista, Jornada, MetaBonus } from '../../types/api'

const today = new Date().toISOString().slice(0, 10)

type RelatorioTab = 'comparativo' | 'performance' | 'exportacao'

function compareStatusTone(item: ComparativoMotorista): 'green' | 'red' {
  const kmPct = item.delta_km_99 != null && item.km_plataformas_99 > 0
    ? Math.abs((item.delta_km_99 / item.km_plataformas_99) * 100)
    : 0
  const faturamentoRelatorio = item.faturamento_uber_relatorio + item.faturamento_99_relatorio
  const faturamentoDeclarado = item.faturamento_uber_declarado + item.faturamento_99_declarado
  const fatPct = faturamentoRelatorio > 0
    ? Math.abs(((faturamentoRelatorio - faturamentoDeclarado) / faturamentoRelatorio) * 100)
    : 0
  return kmPct > 20 || fatPct > 20 ? 'red' : 'green'
}

function matchesDateRange(jornada: Jornada, startDate: string, endDate: string) {
  const data = jornada.data ?? ''
  if (startDate && data < startDate) return false
  if (endDate && data > endDate) return false
  return true
}

function metaMatches(meta: MetaBonus, jornada: Jornada, motoristaId: string) {
  if (meta.referencia.startsWith('MOTORISTA:') && meta.referencia !== `MOTORISTA:${motoristaId}`) {
    return false
  }
  const valor = jornada.faturamento?.total_dia ?? 0
  if (meta.faixa_minima != null && valor < meta.faixa_minima) return false
  if (meta.faixa_maxima != null && valor > meta.faixa_maxima) return false
  return true
}

function downloadCsv(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function RelatoriosPage() {
  const [tab, setTab] = useState<RelatorioTab>('comparativo')
  const [plataforma, setPlataforma] = useState<PlataformaRelatorio>('UBER')
  const [arquivo, setArquivo] = useState<File | null>(null)
  const [compareDate, setCompareDate] = useState(today)
  const [motoristaNome, setMotoristaNome] = useState('')
  const [requestedFilters, setRequestedFilters] = useState({ data: today, motorista_nome: '' })
  const [performanceDriverId, setPerformanceDriverId] = useState('')
  const [exportStartDate, setExportStartDate] = useState('')
  const [exportEndDate, setExportEndDate] = useState('')
  const [exportDriverId, setExportDriverId] = useState('')
  const [importFeedback, setImportFeedback] = useState('')

  const importMutation = useImportRelatorio()
  const comparativoQuery = useComparativoRelatorio(requestedFilters)
  const jornadasQuery = useJornadas({ limit: 200 })
  const motoristasQuery = useMotoristas()
  const metasQuery = useMetas()

  const motoristas = useMemo(() => motoristasQuery.data ?? [], [motoristasQuery.data])
  const motoristasById = useMemo(
    () => motoristas.reduce<Record<string, string>>((acc, motorista) => {
      acc[motorista.id] = motorista.nome
      return acc
    }, {}),
    [motoristas],
  )

  const performanceRows = useMemo(() => {
    const metas = metasQuery.data ?? []
    const grouped = new Map<string, {
      motoristaId: string
      motorista: string
      jornadas: number
      faturamento: number
      km: number
      segundos: number
      metasCumpridas: number
    }>()

    ;(jornadasQuery.data ?? []).forEach((jornada) => {
      const motoristaId = jornada.motorista_id
      const current = grouped.get(motoristaId) ?? {
        motoristaId,
        motorista: motoristasById[motoristaId] ?? motoristaId,
        jornadas: 0,
        faturamento: 0,
        km: 0,
        segundos: 0,
        metasCumpridas: 0,
      }

      current.jornadas += 1
      current.faturamento += jornada.faturamento?.total_dia ?? 0
      current.km += jornada.km?.rodados ?? 0
      current.segundos += jornada.horario?.total_horas_segundos ?? 0
      if (metas.some((meta) => metaMatches(meta, jornada, motoristaId))) {
        current.metasCumpridas += 1
      }
      grouped.set(motoristaId, current)
    })

    const rows = Array.from(grouped.values())
    const maxFat = Math.max(...rows.map((row) => row.faturamento / Math.max(row.jornadas, 1)), 1)
    const maxKm = Math.max(...rows.map((row) => row.km / Math.max(row.jornadas, 1)), 1)

    return rows.map((row) => {
      const faturamentoMedio = row.faturamento / Math.max(row.jornadas, 1)
      const kmMedio = row.km / Math.max(row.jornadas, 1)
      const horasMedia = row.segundos / Math.max(row.jornadas, 1)
      return {
        ...row,
        faturamentoScore: Number(((faturamentoMedio / maxFat) * 100).toFixed(1)),
        kmScore: Number(((kmMedio / maxKm) * 100).toFixed(1)),
        horasScore: Number(Math.min((horasMedia / (8 * 3600)) * 100, 100).toFixed(1)),
        metasScore: Number(((row.metasCumpridas / Math.max(row.jornadas, 1)) * 100).toFixed(1)),
      }
    }).sort((a, b) => b.faturamentoScore - a.faturamentoScore)
  }, [jornadasQuery.data, metasQuery.data, motoristasById])

  const selectedPerformanceDriverId = performanceDriverId || performanceRows[0]?.motoristaId || ''
  const selectedPerformance = performanceRows.find((row) => row.motoristaId === selectedPerformanceDriverId)
  const radarData = selectedPerformance ? [
    { metrica: 'Faturamento médio/dia', valor: selectedPerformance.faturamentoScore },
    { metrica: 'KM médio/dia', valor: selectedPerformance.kmScore },
    { metrica: 'Horas vs meta CLT', valor: selectedPerformance.horasScore },
    { metrica: 'Cumprimento de metas', valor: selectedPerformance.metasScore },
  ] : []

  const exportRows = useMemo(() => {
    return (jornadasQuery.data ?? [])
      .filter((jornada) => matchesDateRange(jornada, exportStartDate, exportEndDate))
      .filter((jornada) => (exportDriverId ? jornada.motorista_id === exportDriverId : true))
  }, [exportDriverId, exportEndDate, exportStartDate, jornadasQuery.data])

  function handleFileInput(event: ChangeEvent<HTMLInputElement>) {
    setArquivo(event.target.files?.[0] ?? null)
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setArquivo(event.dataTransfer.files?.[0] ?? null)
  }

  async function handleImport() {
    if (!arquivo) return
    const response = await importMutation.mutateAsync({ plataforma, arquivo })
    setImportFeedback(`${response.importadas} registro(s) importados com sucesso.`)
    setRequestedFilters({ data: compareDate, motorista_nome: motoristaNome })
  }

  function handleCompare() {
    setRequestedFilters({ data: compareDate, motorista_nome: motoristaNome })
  }

  function handleExportCsv() {
    const header = ['data', 'motorista', 'veiculo', 'status', 'km_rodados', 'faturamento_total', 'horas', 'bonus_mes']
    const lines = exportRows.map((jornada) => [
      jornada.data ?? '',
      motoristasById[jornada.motorista_id] ?? jornada.motorista_id,
      jornada.veiculo_id,
      jornada.status,
      jornada.km?.rodados ?? '',
      jornada.faturamento?.total_dia ?? '',
      formatHoursFromSeconds(jornada.horario?.total_horas_segundos),
      jornada.bonus_acumulado_mes ?? '',
    ].join(';'))

    downloadCsv(`jornadas-${new Date().toISOString().slice(0, 10)}.csv`, [header.join(';'), ...lines].join('\n'))
  }

  const comparativos = comparativoQuery.data?.motoristas ?? []
  const isLoadingBase = jornadasQuery.isLoading || motoristasQuery.isLoading || metasQuery.isLoading
  const hasErrorBase = jornadasQuery.isError || motoristasQuery.isError || metasQuery.isError

  return (
    <section>
      <PageHeader title="Relatórios" subtitle="Importação CSV, comparativo, performance e exportação" />

      <div className="tabs-row">
        <button type="button" className={tab === 'comparativo' ? 'tab-button active' : 'tab-button'} onClick={() => setTab('comparativo')}>Comparativo</button>
        <button type="button" className={tab === 'performance' ? 'tab-button active' : 'tab-button'} onClick={() => setTab('performance')}>Performance</button>
        <button type="button" className={tab === 'exportacao' ? 'tab-button active' : 'tab-button'} onClick={() => setTab('exportacao')}>Exportação</button>
      </div>

      {tab === 'comparativo' ? (
        <>
          <article className="card">
            <div className="form-grid">
              <label>
                <span>Plataforma</span>
                <select value={plataforma} onChange={(event) => setPlataforma(event.target.value as PlataformaRelatorio)}>
                  <option value="UBER">Uber</option>
                  <option value="99">99</option>
                </select>
              </label>
              <label>
                <span>Data</span>
                <input type="date" value={compareDate} onChange={(event) => setCompareDate(event.target.value)} />
              </label>
              <label>
                <span>Motorista</span>
                <select value={motoristaNome} onChange={(event) => setMotoristaNome(event.target.value)}>
                  <option value="">Todos</option>
                  {motoristas.map((motorista) => (
                    <option key={motorista.id} value={motorista.nome}>{motorista.nome}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="dropzone" onDragOver={(event) => event.preventDefault()} onDrop={handleDrop}>
              <p>{arquivo ? arquivo.name : 'Arraste o CSV aqui ou selecione um arquivo.'}</p>
              <input type="file" accept=".csv,text/csv" onChange={handleFileInput} />
            </div>
            <div className="card-actions">
              <button type="button" onClick={handleImport} disabled={!arquivo || importMutation.isPending}>
                {importMutation.isPending ? 'Importando...' : 'Importar CSV'}
              </button>
              <button type="button" className="secondary-button" onClick={handleCompare}>
                Atualizar comparativo
              </button>
            </div>
            {importFeedback ? <p className="success-text">{importFeedback}</p> : null}
            {importMutation.isError ? <p className="error-text">Falha ao importar o CSV.</p> : null}
            {comparativoQuery.isError ? <p className="error-text">Falha ao carregar comparativo.</p> : null}
          </article>

          <article className="card">
            <div className="section-header">
              <div>
                <h3>Comparativo por motorista</h3>
                <p>{comparativoQuery.data?.total_motoristas ?? 0} motorista(s) no recorte atual.</p>
              </div>
            </div>
            {comparativoQuery.isLoading ? <p className="empty-state">Carregando comparativo...</p> : null}
            {!comparativoQuery.isLoading && comparativos.length === 0 ? <p className="empty-state">Nenhum dado comparativo disponível.</p> : null}
            {!comparativoQuery.isLoading && comparativos.length > 0 ? (
              <table className="table">
                <thead>
                  <tr>
                    <th>Motorista</th>
                    <th>Data</th>
                    <th>KM jornada</th>
                    <th>KM plataforma</th>
                    <th>Delta KM %</th>
                    <th>Fat. declarado</th>
                    <th>Fat. plataforma</th>
                    <th>Delta Fat. %</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {comparativos.map((item) => {
                    const kmPct = item.delta_km_99 != null && item.km_plataformas_99 > 0
                      ? (item.delta_km_99 / item.km_plataformas_99) * 100
                      : 0
                    const faturamentoRelatorio = item.faturamento_uber_relatorio + item.faturamento_99_relatorio
                    const faturamentoDeclarado = item.faturamento_uber_declarado + item.faturamento_99_declarado
                    const fatPct = faturamentoRelatorio > 0
                      ? ((faturamentoRelatorio - faturamentoDeclarado) / faturamentoRelatorio) * 100
                      : 0

                    return (
                      <tr key={`${item.motorista_nome}-${item.data}`}>
                        <td>{item.motorista_nome}</td>
                        <td>{toShortDate(item.data)}</td>
                        <td>{item.jornada_km_rodados?.toFixed(1) ?? '-'}</td>
                        <td>{item.km_plataformas_99.toFixed(1)}</td>
                        <td>{kmPct.toFixed(1)}%</td>
                        <td>{formatCurrency(faturamentoDeclarado)}</td>
                        <td>{formatCurrency(faturamentoRelatorio)}</td>
                        <td>{fatPct.toFixed(1)}%</td>
                        <td><StatusBadge label={compareStatusTone(item) === 'green' ? 'OK' : 'Atenção'} tone={compareStatusTone(item)} /></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            ) : null}
          </article>
        </>
      ) : null}

      {tab === 'performance' ? (
        <>
          {isLoadingBase ? <p className="empty-state">Carregando performance...</p> : null}
          {hasErrorBase ? <p className="error-text">Falha ao carregar dados de performance.</p> : null}
          {!isLoadingBase && !hasErrorBase ? (
            <>
              <article className="card">
                <div className="filters">
                  <label>
                    <span>Motorista</span>
                    <select value={selectedPerformanceDriverId} onChange={(event) => setPerformanceDriverId(event.target.value)}>
                      {performanceRows.map((row) => (
                        <option key={row.motoristaId} value={row.motoristaId}>{row.motorista}</option>
                      ))}
                    </select>
                  </label>
                </div>
              </article>

              <article className="card chart-card">
                <div className="section-header">
                  <div>
                    <h3>Radar de performance</h3>
                    <p>{selectedPerformance?.motorista ?? 'Sem motorista selecionado'}</p>
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={320}>
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="metrica" />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} />
                    <Radar dataKey="valor" stroke="#2563eb" fill="#2563eb" fillOpacity={0.5} />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </article>

              <article className="card">
                <h3>Ranking resumido</h3>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Motorista</th>
                      <th>Faturamento</th>
                      <th>KM</th>
                      <th>Horas CLT</th>
                      <th>Metas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {performanceRows.map((row) => (
                      <tr key={row.motoristaId}>
                        <td>{row.motorista}</td>
                        <td>{row.faturamentoScore}</td>
                        <td>{row.kmScore}</td>
                        <td>{row.horasScore}</td>
                        <td>{row.metasScore}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </article>
            </>
          ) : null}
        </>
      ) : null}

      {tab === 'exportacao' ? (
        <>
          {isLoadingBase ? <p className="empty-state">Carregando jornadas para exportação...</p> : null}
          {hasErrorBase ? <p className="error-text">Falha ao preparar exportação.</p> : null}
          {!isLoadingBase && !hasErrorBase ? (
            <>
              <article className="card">
                <div className="filters">
                  <label>
                    <span>Data inicial</span>
                    <input type="date" value={exportStartDate} onChange={(event) => setExportStartDate(event.target.value)} />
                  </label>
                  <label>
                    <span>Data final</span>
                    <input type="date" value={exportEndDate} onChange={(event) => setExportEndDate(event.target.value)} />
                  </label>
                  <label>
                    <span>Motorista</span>
                    <select value={exportDriverId} onChange={(event) => setExportDriverId(event.target.value)}>
                      <option value="">Todos</option>
                      {motoristas.map((motorista) => (
                        <option key={motorista.id} value={motorista.id}>{motorista.nome}</option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="card-actions">
                  <button type="button" onClick={handleExportCsv} disabled={exportRows.length === 0}>Exportar CSV</button>
                </div>
              </article>

              <article className="card">
                <h3>Prévia da exportação</h3>
                {exportRows.length === 0 ? <p className="empty-state">Nenhuma jornada no filtro atual.</p> : (
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Motorista</th>
                        <th>Veículo</th>
                        <th>Status</th>
                        <th>Faturamento</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exportRows.map((jornada) => (
                        <tr key={jornada.id}>
                          <td>{toShortDate(jornada.data)}</td>
                          <td>{motoristasById[jornada.motorista_id] ?? jornada.motorista_id}</td>
                          <td>{jornada.veiculo_id}</td>
                          <td>{jornada.status}</td>
                          <td>{formatCurrency(jornada.faturamento?.total_dia)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </article>
            </>
          ) : null}
        </>
      ) : null}
    </section>
  )
}
