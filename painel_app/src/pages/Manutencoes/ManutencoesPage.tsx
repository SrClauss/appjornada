import { useMemo, useState, type FormEvent } from 'react'
import {
  useCreateManutencao,
  useManutencoes,
  useUpdateManutencao,
  type CreateManutencaoPayload,
  type UpdateManutencaoPayload,
} from '../../api/hooks/useManutencoes'
import { useMotoristas } from '../../api/hooks/useMotoristas'
import { useVeiculos } from '../../api/hooks/useVeiculos'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageHeader } from '../../components/shared/PageHeader'
import { toShortDateTime } from '../../lib/formatters'
import { formatCurrency, parseOptionalNumber } from '../../lib/utils'
import type { Manutencao } from '../../types/api'

interface ManutencaoFormState {
  veiculo_id: string
  motorista_id: string
  entrada: string
  saida: string
  duracao_minutos: string
  km: string
  km_proxima_revisao: string
  status: string
  oficina: string
  decisao: string
  servico_tipo: string
  servico_descricao: string
  servico_valor: string
  servico_foto_nf_url: string
}

const emptyForm: ManutencaoFormState = {
  veiculo_id: '',
  motorista_id: '',
  entrada: '',
  saida: '',
  duracao_minutos: '',
  km: '',
  km_proxima_revisao: '',
  status: 'EM_ANDAMENTO',
  oficina: '',
  decisao: '',
  servico_tipo: '',
  servico_descricao: '',
  servico_valor: '',
  servico_foto_nf_url: '',
}

function maintenanceTone(status?: string): 'green' | 'yellow' | 'red' | 'blue' | 'gray' {
  if (status === 'CONCLUIDA') return 'green'
  if (status === 'EM_ANDAMENTO') return 'yellow'
  if (status === 'CANCELADA') return 'red'
  if (status === 'AGENDADA') return 'blue'
  return 'gray'
}

function formFromManutencao(manutencao: Manutencao): ManutencaoFormState {
  return {
    veiculo_id: manutencao.veiculo_id,
    motorista_id: manutencao.motorista_id ?? '',
    entrada: manutencao.entrada?.slice(0, 16) ?? '',
    saida: manutencao.saida?.slice(0, 16) ?? '',
    duracao_minutos: manutencao.duracao_minutos?.toString() ?? '',
    km: manutencao.km?.toString() ?? '',
    km_proxima_revisao: manutencao.km_proxima_revisao?.toString() ?? '',
    status: manutencao.status,
    oficina: manutencao.oficina ?? '',
    decisao: manutencao.decisao ?? '',
    servico_tipo: manutencao.servico?.tipo ?? '',
    servico_descricao: manutencao.servico?.descricao ?? '',
    servico_valor: manutencao.servico?.valor?.toString() ?? '',
    servico_foto_nf_url: manutencao.servico?.foto_nf_url ?? '',
  }
}

function createPayload(form: ManutencaoFormState): CreateManutencaoPayload {
  return {
    veiculo_id: form.veiculo_id,
    motorista_id: form.motorista_id || undefined,
    entrada: form.entrada || undefined,
    saida: form.saida || undefined,
    duracao_minutos: parseOptionalNumber(form.duracao_minutos),
    km: parseOptionalNumber(form.km),
    km_proxima_revisao: parseOptionalNumber(form.km_proxima_revisao),
    status: form.status,
    oficina: form.oficina.trim() || undefined,
    decisao: form.decisao.trim() || undefined,
    servico: {
      tipo: form.servico_tipo.trim() || undefined,
      descricao: form.servico_descricao.trim() || undefined,
      valor: parseOptionalNumber(form.servico_valor),
      foto_nf_url: form.servico_foto_nf_url.trim() || undefined,
    },
  }
}

function updatePayload(form: ManutencaoFormState): UpdateManutencaoPayload {
  return {
    saida: form.saida || undefined,
    duracao_minutos: parseOptionalNumber(form.duracao_minutos),
    km: parseOptionalNumber(form.km),
    km_proxima_revisao: parseOptionalNumber(form.km_proxima_revisao),
    status: form.status,
    oficina: form.oficina.trim() || undefined,
    decisao: form.decisao.trim() || undefined,
    servico: {
      tipo: form.servico_tipo.trim() || undefined,
      descricao: form.servico_descricao.trim() || undefined,
      valor: parseOptionalNumber(form.servico_valor),
      foto_nf_url: form.servico_foto_nf_url.trim() || undefined,
    },
  }
}

export function ManutencoesPage() {
  const manutencoesQuery = useManutencoes()
  const veiculosQuery = useVeiculos()
  const motoristasQuery = useMotoristas()
  const createMutation = useCreateManutencao()
  const [selectedManutencao, setSelectedManutencao] = useState<Manutencao | null>(null)
  const [form, setForm] = useState<ManutencaoFormState>(emptyForm)
  const updateMutation = useUpdateManutencao(selectedManutencao?.id)

  const manutencoes = useMemo(
    () => [...(manutencoesQuery.data ?? [])].sort((a, b) => `${b.entrada ?? ''}`.localeCompare(`${a.entrada ?? ''}`)),
    [manutencoesQuery.data],
  )
  const veiculos = veiculosQuery.data ?? []
  const motoristas = motoristasQuery.data ?? []
  const veiculosById = useMemo(
    () => veiculos.reduce<Record<string, number | undefined>>((acc, veiculo) => {
      acc[veiculo.id_placa] = veiculo.km_atual
      return acc
    }, {}),
    [veiculos],
  )

  const kpis = useMemo(() => {
    const now = new Date()
    const totalMes = manutencoes.reduce((acc, manutencao) => {
      if (!manutencao.entrada) return acc
      const data = new Date(manutencao.entrada)
      const sameMonth = data.getMonth() === now.getMonth() && data.getFullYear() === now.getFullYear()
      return sameMonth ? acc + (manutencao.servico?.valor ?? 0) : acc
    }, 0)

    const emAndamento = manutencoes.filter((manutencao) => manutencao.status === 'EM_ANDAMENTO').length
    const proximos = new Set(
      manutencoes
        .filter((manutencao) => {
          const kmAtual = veiculosById[manutencao.veiculo_id]
          const proxima = manutencao.km_proxima_revisao
          if (kmAtual == null || proxima == null) return false
          const restante = proxima - kmAtual
          return restante >= 0 && restante <= 500
        })
        .map((manutencao) => manutencao.veiculo_id),
    ).size

    return { totalMes, emAndamento, proximos }
  }, [manutencoes, veiculosById])

  function resetForm() {
    setSelectedManutencao(null)
    setForm(emptyForm)
  }

  function handleEdit(manutencao: Manutencao) {
    setSelectedManutencao(manutencao)
    setForm(formFromManutencao(manutencao))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form.veiculo_id) return

    if (selectedManutencao) {
      await updateMutation.mutateAsync(updatePayload(form))
    } else {
      await createMutation.mutateAsync(createPayload(form))
    }

    resetForm()
  }

  const isSaving = createMutation.isPending || updateMutation.isPending
  const isLoading = manutencoesQuery.isLoading || veiculosQuery.isLoading || motoristasQuery.isLoading
  const hasError = manutencoesQuery.isError || veiculosQuery.isError || motoristasQuery.isError

  return (
    <section>
      <PageHeader title="Manutenções" subtitle="KPIs mensais e controle de serviços" />

      <div className="kpi-grid">
        <article className="card"><h3>Custo no mês</h3><strong>{formatCurrency(kpis.totalMes)}</strong></article>
        <article className="card"><h3>Em andamento</h3><strong>{kpis.emAndamento}</strong></article>
        <article className="card"><h3>Próximos da revisão</h3><strong>{kpis.proximos}</strong></article>
      </div>

      <article className="card">
        <div className="section-header">
          <div>
            <h3>{selectedManutencao ? 'Atualizar manutenção' : 'Nova manutenção'}</h3>
            <p>{selectedManutencao ? 'Edite o serviço selecionado.' : 'Registre uma nova manutenção da frota.'}</p>
          </div>
          {selectedManutencao ? <button type="button" className="secondary-button" onClick={resetForm}>Cancelar edição</button> : null}
        </div>

        <form className="form-grid" onSubmit={handleSubmit}>
          <label>
            <span>Veículo</span>
            <select value={form.veiculo_id} onChange={(event) => setForm((current) => ({ ...current, veiculo_id: event.target.value }))} disabled={Boolean(selectedManutencao)} required>
              <option value="">Selecione</option>
              {veiculos.map((veiculo) => (
                <option key={veiculo.id} value={veiculo.id_placa}>{veiculo.id_placa}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Motorista</span>
            <select value={form.motorista_id} onChange={(event) => setForm((current) => ({ ...current, motorista_id: event.target.value }))} disabled={Boolean(selectedManutencao)}>
              <option value="">Não vinculado</option>
              {motoristas.map((motorista) => (
                <option key={motorista.id} value={motorista.id}>{motorista.nome}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Entrada</span>
            <input type="datetime-local" value={form.entrada} onChange={(event) => setForm((current) => ({ ...current, entrada: event.target.value }))} disabled={Boolean(selectedManutencao)} />
          </label>
          <label>
            <span>Saída</span>
            <input type="datetime-local" value={form.saida} onChange={(event) => setForm((current) => ({ ...current, saida: event.target.value }))} />
          </label>
          <label>
            <span>Duração (min)</span>
            <input value={form.duracao_minutos} onChange={(event) => setForm((current) => ({ ...current, duracao_minutos: event.target.value }))} />
          </label>
          <label>
            <span>KM</span>
            <input value={form.km} onChange={(event) => setForm((current) => ({ ...current, km: event.target.value }))} />
          </label>
          <label>
            <span>Próxima revisão (KM)</span>
            <input value={form.km_proxima_revisao} onChange={(event) => setForm((current) => ({ ...current, km_proxima_revisao: event.target.value }))} />
          </label>
          <label>
            <span>Status</span>
            <select value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}>
              <option value="AGENDADA">AGENDADA</option>
              <option value="EM_ANDAMENTO">EM_ANDAMENTO</option>
              <option value="CONCLUIDA">CONCLUIDA</option>
              <option value="CANCELADA">CANCELADA</option>
            </select>
          </label>
          <label>
            <span>Oficina</span>
            <input value={form.oficina} onChange={(event) => setForm((current) => ({ ...current, oficina: event.target.value }))} />
          </label>
          <label>
            <span>Decisão</span>
            <input value={form.decisao} onChange={(event) => setForm((current) => ({ ...current, decisao: event.target.value }))} />
          </label>
          <label>
            <span>Tipo de serviço</span>
            <input value={form.servico_tipo} onChange={(event) => setForm((current) => ({ ...current, servico_tipo: event.target.value }))} />
          </label>
          <label>
            <span>Descrição</span>
            <input value={form.servico_descricao} onChange={(event) => setForm((current) => ({ ...current, servico_descricao: event.target.value }))} />
          </label>
          <label>
            <span>Valor</span>
            <input value={form.servico_valor} onChange={(event) => setForm((current) => ({ ...current, servico_valor: event.target.value }))} />
          </label>
          <label>
            <span>Nota fiscal (URL)</span>
            <input value={form.servico_foto_nf_url} onChange={(event) => setForm((current) => ({ ...current, servico_foto_nf_url: event.target.value }))} />
          </label>
          <div className="form-actions">
            <button type="submit" disabled={isSaving}>{isSaving ? 'Salvando...' : selectedManutencao ? 'Atualizar manutenção' : 'Registrar manutenção'}</button>
          </div>
        </form>
      </article>

      {isLoading ? <p className="empty-state">Carregando manutenções...</p> : null}
      {hasError ? <p className="error-text">Falha ao carregar dados de manutenção.</p> : null}

      {!isLoading && !hasError ? (
        <article className="card">
          <h3>Histórico de manutenções</h3>
          {manutencoes.length === 0 ? <p className="empty-state">Nenhuma manutenção cadastrada.</p> : (
            <table className="table">
              <thead>
                <tr>
                  <th>Veículo</th>
                  <th>Entrada</th>
                  <th>Status</th>
                  <th>Oficina</th>
                  <th>Serviço</th>
                  <th>Custo</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {manutencoes.map((manutencao) => (
                  <tr key={manutencao.id}>
                    <td>{manutencao.veiculo_id}</td>
                    <td>{toShortDateTime(manutencao.entrada)}</td>
                    <td><StatusBadge label={manutencao.status} tone={maintenanceTone(manutencao.status)} /></td>
                    <td>{manutencao.oficina ?? '-'}</td>
                    <td>{manutencao.servico?.descricao ?? manutencao.servico?.tipo ?? '-'}</td>
                    <td>{formatCurrency(manutencao.servico?.valor)}</td>
                    <td>
                      <button type="button" className="secondary-button" onClick={() => handleEdit(manutencao)}>Editar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </article>
      ) : null}
    </section>
  )
}
