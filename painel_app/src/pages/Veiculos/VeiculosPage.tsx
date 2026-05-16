import { useMemo, useState, type FormEvent } from 'react'
import { useCreateVeiculo, useUpdateVeiculo, useVeiculos, type VeiculoPayload } from '../../api/hooks/useVeiculos'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageHeader } from '../../components/shared/PageHeader'
import { cnhStatus, cnhStatusLabel, toShortDate } from '../../lib/formatters'
import { parseOptionalNumber } from '../../lib/utils'
import type { Veiculo } from '../../types/api'

interface VeiculoFormState {
  id_placa: string
  marca_modelo: string
  ano_modelo: string
  cor: string
  situacao: string
  km_atual: string
  vencimento_ipva: string
  imagem_clrv_url: string
}

const emptyForm: VeiculoFormState = {
  id_placa: '',
  marca_modelo: '',
  ano_modelo: '',
  cor: '',
  situacao: 'RODANDO',
  km_atual: '',
  vencimento_ipva: '',
  imagem_clrv_url: '',
}

function vehicleTone(status?: string): 'green' | 'blue' | 'yellow' | 'red' | 'gray' {
  if (status === 'RODANDO') return 'green'
  if (status === 'RESERVA') return 'blue'
  if (status === 'MANUTENCAO') return 'yellow'
  if (status === 'INATIVO') return 'red'
  return 'gray'
}

function buildPayload(form: VeiculoFormState): VeiculoPayload {
  return {
    id_placa: form.id_placa.trim().toUpperCase(),
    marca_modelo: form.marca_modelo.trim() || undefined,
    ano_modelo: form.ano_modelo.trim() || undefined,
    cor: form.cor.trim() || undefined,
    situacao: form.situacao,
    km_atual: parseOptionalNumber(form.km_atual),
    vencimento_ipva: form.vencimento_ipva || undefined,
    imagem_clrv_url: form.imagem_clrv_url.trim() || undefined,
  }
}

function formFromVeiculo(veiculo: Veiculo): VeiculoFormState {
  return {
    id_placa: veiculo.id_placa,
    marca_modelo: veiculo.marca_modelo ?? '',
    ano_modelo: veiculo.ano_modelo ?? '',
    cor: veiculo.cor ?? '',
    situacao: veiculo.situacao,
    km_atual: veiculo.km_atual?.toString() ?? '',
    vencimento_ipva: veiculo.vencimento_ipva ?? '',
    imagem_clrv_url: veiculo.imagem_clrv_url ?? '',
  }
}

export function VeiculosPage() {
  const veiculosQuery = useVeiculos()
  const createMutation = useCreateVeiculo()
  const [selectedVeiculo, setSelectedVeiculo] = useState<Veiculo | null>(null)
  const [form, setForm] = useState<VeiculoFormState>(emptyForm)
  const updateMutation = useUpdateVeiculo(selectedVeiculo?.id_placa)

  const veiculos = useMemo(
    () => [...(veiculosQuery.data ?? [])].sort((a, b) => a.id_placa.localeCompare(b.id_placa)),
    [veiculosQuery.data],
  )

  const statusCounts = useMemo(() => {
    return veiculos.reduce<Record<string, number>>((acc, veiculo) => {
      acc[veiculo.situacao] = (acc[veiculo.situacao] ?? 0) + 1
      return acc
    }, {})
  }, [veiculos])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = buildPayload(form)
    if (!payload.id_placa) return

    if (selectedVeiculo) {
      const updatePayload = {
        marca_modelo: payload.marca_modelo,
        ano_modelo: payload.ano_modelo,
        cor: payload.cor,
        situacao: payload.situacao,
        km_atual: payload.km_atual,
        vencimento_ipva: payload.vencimento_ipva,
        imagem_clrv_url: payload.imagem_clrv_url,
      }
      await updateMutation.mutateAsync(updatePayload)
    } else {
      await createMutation.mutateAsync(payload)
    }

    setSelectedVeiculo(null)
    setForm(emptyForm)
  }

  function handleEdit(veiculo: Veiculo) {
    setSelectedVeiculo(veiculo)
    setForm(formFromVeiculo(veiculo))
  }

  function resetForm() {
    setSelectedVeiculo(null)
    setForm(emptyForm)
  }

  const isSaving = createMutation.isPending || updateMutation.isPending

  return (
    <section>
      <PageHeader title="Veículos" subtitle="Cards operacionais e CRUD conectado à API" />

      <div className="status-bar">
        {Object.entries(statusCounts).map(([status, total]) => (
          <article key={status} className="card compact-card">
            <span>{status}</span>
            <strong>{total}</strong>
          </article>
        ))}
      </div>

      <article className="card">
        <div className="section-header">
          <div>
            <h3>{selectedVeiculo ? `Editar ${selectedVeiculo.id_placa}` : 'Novo veículo'}</h3>
            <p>{selectedVeiculo ? 'Atualize os dados do veículo selecionado.' : 'Cadastre um veículo para a frota.'}</p>
          </div>
          {selectedVeiculo ? <button type="button" className="secondary-button" onClick={resetForm}>Cancelar edição</button> : null}
        </div>

        <form className="form-grid" onSubmit={handleSubmit}>
          <label>
            <span>Placa</span>
            <input
              value={form.id_placa}
              onChange={(event) => setForm((current) => ({ ...current, id_placa: event.target.value }))}
              disabled={Boolean(selectedVeiculo)}
              required
            />
          </label>
          <label>
            <span>Marca / modelo</span>
            <input value={form.marca_modelo} onChange={(event) => setForm((current) => ({ ...current, marca_modelo: event.target.value }))} />
          </label>
          <label>
            <span>Ano / modelo</span>
            <input value={form.ano_modelo} onChange={(event) => setForm((current) => ({ ...current, ano_modelo: event.target.value }))} />
          </label>
          <label>
            <span>Cor</span>
            <input value={form.cor} onChange={(event) => setForm((current) => ({ ...current, cor: event.target.value }))} />
          </label>
          <label>
            <span>Status</span>
            <select value={form.situacao} onChange={(event) => setForm((current) => ({ ...current, situacao: event.target.value }))}>
              <option value="RODANDO">RODANDO</option>
              <option value="RESERVA">RESERVA</option>
              <option value="MANUTENCAO">MANUTENCAO</option>
              <option value="INATIVO">INATIVO</option>
            </select>
          </label>
          <label>
            <span>KM atual</span>
            <input value={form.km_atual} onChange={(event) => setForm((current) => ({ ...current, km_atual: event.target.value }))} />
          </label>
          <label>
            <span>Vencimento do IPVA</span>
            <input type="date" value={form.vencimento_ipva} onChange={(event) => setForm((current) => ({ ...current, vencimento_ipva: event.target.value }))} />
          </label>
          <label>
            <span>URL do documento</span>
            <input value={form.imagem_clrv_url} onChange={(event) => setForm((current) => ({ ...current, imagem_clrv_url: event.target.value }))} />
          </label>
          <div className="form-actions">
            <button type="submit" disabled={isSaving}>{isSaving ? 'Salvando...' : selectedVeiculo ? 'Atualizar veículo' : 'Cadastrar veículo'}</button>
          </div>
        </form>
      </article>

      {veiculosQuery.isLoading ? <p className="empty-state">Carregando veículos...</p> : null}
      {veiculosQuery.isError ? <p className="error-text">Falha ao carregar veículos.</p> : null}

      {!veiculosQuery.isLoading && !veiculosQuery.isError ? (
        <div className="cards-grid">
          {veiculos.map((veiculo) => {
            const ipvaStatus = cnhStatus(veiculo.vencimento_ipva)
            return (
              <article key={veiculo.id} className="card vehicle-card">
                <div className="section-header">
                  <div>
                    <h3>{veiculo.id_placa}</h3>
                    <p>{veiculo.marca_modelo ?? 'Modelo não informado'}</p>
                  </div>
                  <StatusBadge label={veiculo.situacao} tone={vehicleTone(veiculo.situacao)} />
                </div>
                <div className="detail-list">
                  <div><span>KM atual</span><strong>{veiculo.km_atual ?? '-'}</strong></div>
                  <div><span>Cor</span><strong>{veiculo.cor ?? '-'}</strong></div>
                  <div><span>Ano</span><strong>{veiculo.ano_modelo ?? '-'}</strong></div>
                  <div><span>IPVA</span><strong>{toShortDate(veiculo.vencimento_ipva)}</strong></div>
                </div>
                <div className="vehicle-alerts">
                  <StatusBadge label={`IPVA ${cnhStatusLabel(ipvaStatus)}`} tone={ipvaStatus === 'VALIDA' ? 'green' : ipvaStatus === 'ATENCAO' ? 'yellow' : ipvaStatus === 'EXPIRADA' ? 'red' : 'gray'} />
                </div>
                <div className="card-actions">
                  <button type="button" className="secondary-button" onClick={() => handleEdit(veiculo)}>Editar</button>
                  {veiculo.imagem_clrv_url ? <a href={veiculo.imagem_clrv_url} target="_blank" rel="noreferrer">Documento</a> : null}
                </div>
              </article>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}
