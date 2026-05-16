import { useMemo, useState, type FormEvent } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useCreateMeta, useDeleteMeta, useMetas, useUpdateMeta, type MetaPayload } from '../../api/hooks/useMetas'
import { useJornadas } from '../../api/hooks/useJornadas'
import { useMotoristas } from '../../api/hooks/useMotoristas'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageHeader } from '../../components/shared/PageHeader'
import { useAuthContext } from '../../contexts/useAuthContext'
import { formatCurrency, parseOptionalNumber } from '../../lib/utils'
import type { MetaBonus } from '../../types/api'

interface MetaFormState {
  tipo: string
  escopo: 'GERAL' | 'EQUIPE' | 'INDIVIDUAL'
  motorista_id: string
  faixa_minima: string
  faixa_maxima: string
  bonus: string
}

const emptyForm: MetaFormState = {
  tipo: 'FATURAMENTO',
  escopo: 'GERAL',
  motorista_id: '',
  faixa_minima: '',
  faixa_maxima: '',
  bonus: '',
}

function parseReferencia(reference: string): Pick<MetaFormState, 'escopo' | 'motorista_id'> {
  if (reference.startsWith('MOTORISTA:')) {
    return { escopo: 'INDIVIDUAL', motorista_id: reference.replace('MOTORISTA:', '') }
  }
  if (reference === 'EQUIPE') {
    return { escopo: 'EQUIPE', motorista_id: '' }
  }
  return { escopo: 'GERAL', motorista_id: '' }
}

function buildPayload(form: MetaFormState): MetaPayload {
  return {
    tipo: form.tipo,
    referencia: form.escopo === 'INDIVIDUAL' && form.motorista_id ? `MOTORISTA:${form.motorista_id}` : form.escopo,
    faixa_minima: parseOptionalNumber(form.faixa_minima),
    faixa_maxima: parseOptionalNumber(form.faixa_maxima),
    bonus: parseOptionalNumber(form.bonus),
  }
}

function formFromMeta(meta: MetaBonus): MetaFormState {
  const referencia = parseReferencia(meta.referencia)
  return {
    tipo: meta.tipo,
    escopo: referencia.escopo,
    motorista_id: referencia.motorista_id,
    faixa_minima: meta.faixa_minima?.toString() ?? '',
    faixa_maxima: meta.faixa_maxima?.toString() ?? '',
    bonus: meta.bonus?.toString() ?? '',
  }
}

function referenceLabel(reference: string, motoristaMap: Record<string, string>) {
  if (reference.startsWith('MOTORISTA:')) {
    const motoristaId = reference.replace('MOTORISTA:', '')
    return `Individual · ${motoristaMap[motoristaId] ?? motoristaId}`
  }
  if (reference === 'EQUIPE') return 'Equipe'
  return 'Geral'
}

export function MetasPage() {
  const { user } = useAuthContext()
  const metasQuery = useMetas()
  const jornadasQuery = useJornadas({ limit: 200 })
  const motoristasQuery = useMotoristas()
  const createMutation = useCreateMeta()
  const deleteMutation = useDeleteMeta()
  const [selectedMeta, setSelectedMeta] = useState<MetaBonus | null>(null)
  const [form, setForm] = useState<MetaFormState>(emptyForm)
  const updateMutation = useUpdateMeta(selectedMeta?.id)

  const motoristas = useMemo(() => motoristasQuery.data ?? [], [motoristasQuery.data])
  const motoristaMap = useMemo(
    () => motoristas.reduce<Record<string, string>>((acc, motorista) => {
      acc[motorista.id] = motorista.nome
      return acc
    }, {}),
    [motoristas],
  )

  const bonusChartData = useMemo(() => {
    const currentMonth = new Date().toISOString().slice(0, 7)
    const grouped = new Map<string, { motorista: string; bonus: number }>()

    ;(jornadasQuery.data ?? [])
      .filter((jornada) => jornada.data?.startsWith(currentMonth))
      .forEach((jornada) => {
        const current = grouped.get(jornada.motorista_id)
        const bonus = jornada.bonus_acumulado_mes ?? 0
        if (!current || bonus > current.bonus) {
          grouped.set(jornada.motorista_id, {
            motorista: motoristaMap[jornada.motorista_id] ?? jornada.motorista_id,
            bonus,
          })
        }
      })

    return Array.from(grouped.values()).sort((a, b) => b.bonus - a.bonus)
  }, [jornadasQuery.data, motoristaMap])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const payload = buildPayload(form)

    if (selectedMeta) {
      await updateMutation.mutateAsync(payload)
    } else {
      await createMutation.mutateAsync(payload)
    }

    setSelectedMeta(null)
    setForm(emptyForm)
  }

  function handleEdit(meta: MetaBonus) {
    setSelectedMeta(meta)
    setForm(formFromMeta(meta))
  }

  function resetForm() {
    setSelectedMeta(null)
    setForm(emptyForm)
  }

  async function handleDelete(id: string) {
    await deleteMutation.mutateAsync(id)
    if (selectedMeta?.id === id) {
      resetForm()
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending
  const isLoading = metasQuery.isLoading || jornadasQuery.isLoading || motoristasQuery.isLoading
  const hasError = metasQuery.isError || jornadasQuery.isError || motoristasQuery.isError

  return (
    <section>
      <PageHeader title="Metas" subtitle="Faixas de bônus e evolução mensal por motorista" />

      <article className="card chart-card">
        <div className="section-header">
          <div>
            <h3>Bônus acumulado no mês</h3>
            <p>Maior valor acumulado encontrado por motorista nas jornadas do mês.</p>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={bonusChartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="motorista" />
            <YAxis />
            <Tooltip formatter={(value) => formatCurrency(Number(value))} />
            <Bar dataKey="bonus" fill="#7c3aed" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </article>

      <article className="card">
        <div className="section-header">
          <div>
            <h3>{selectedMeta ? 'Editar meta' : 'Nova meta'}</h3>
            <p>{selectedMeta ? 'Ajuste a regra de bônus selecionada.' : 'Cadastre uma nova faixa de bônus.'}</p>
          </div>
          {selectedMeta ? <button type="button" className="secondary-button" onClick={resetForm}>Cancelar edição</button> : null}
        </div>

        <form className="form-grid" onSubmit={handleSubmit}>
          <label>
            <span>Tipo</span>
            <select value={form.tipo} onChange={(event) => setForm((current) => ({ ...current, tipo: event.target.value }))}>
              <option value="FATURAMENTO">Faturamento</option>
              <option value="KM">KM</option>
              <option value="HORAS">Horas</option>
            </select>
          </label>
          <label>
            <span>Escopo</span>
            <select value={form.escopo} onChange={(event) => setForm((current) => ({ ...current, escopo: event.target.value as MetaFormState['escopo'] }))}>
              <option value="GERAL">Geral</option>
              <option value="EQUIPE">Equipe</option>
              <option value="INDIVIDUAL">Individual</option>
            </select>
          </label>
          {form.escopo === 'INDIVIDUAL' ? (
            <label>
              <span>Motorista</span>
              <select value={form.motorista_id} onChange={(event) => setForm((current) => ({ ...current, motorista_id: event.target.value }))} required>
                <option value="">Selecione</option>
                {motoristas.map((motorista) => (
                  <option key={motorista.id} value={motorista.id}>{motorista.nome}</option>
                ))}
              </select>
            </label>
          ) : null}
          <label>
            <span>Faixa mínima</span>
            <input value={form.faixa_minima} onChange={(event) => setForm((current) => ({ ...current, faixa_minima: event.target.value }))} />
          </label>
          <label>
            <span>Faixa máxima</span>
            <input value={form.faixa_maxima} onChange={(event) => setForm((current) => ({ ...current, faixa_maxima: event.target.value }))} />
          </label>
          <label>
            <span>Bônus</span>
            <input value={form.bonus} onChange={(event) => setForm((current) => ({ ...current, bonus: event.target.value }))} />
          </label>
          <div className="form-actions">
            <button type="submit" disabled={isSaving}>{isSaving ? 'Salvando...' : selectedMeta ? 'Atualizar meta' : 'Cadastrar meta'}</button>
          </div>
        </form>
      </article>

      {isLoading ? <p className="empty-state">Carregando metas...</p> : null}
      {hasError ? <p className="error-text">Falha ao carregar metas.</p> : null}

      {!isLoading && !hasError ? (
        <article className="card">
          <h3>Regras cadastradas</h3>
          {(metasQuery.data ?? []).length === 0 ? <p className="empty-state">Nenhuma meta cadastrada.</p> : (
            <table className="table">
              <thead>
                <tr>
                  <th>Tipo</th>
                  <th>Escopo</th>
                  <th>Faixa</th>
                  <th>Bônus</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {(metasQuery.data ?? []).map((meta) => (
                  <tr key={meta.id}>
                    <td><StatusBadge label={meta.tipo} tone="purple" /></td>
                    <td>{referenceLabel(meta.referencia, motoristaMap)}</td>
                    <td>
                      {meta.faixa_minima ?? '-'} → {meta.faixa_maxima ?? 'sem teto'}
                    </td>
                    <td>{formatCurrency(meta.bonus)}</td>
                    <td>
                      <div className="table-actions">
                        <button type="button" className="secondary-button" onClick={() => handleEdit(meta)}>Editar</button>
                        {user?.role === 'ADMIN' ? (
                          <button type="button" className="danger-button" onClick={() => handleDelete(meta.id)} disabled={deleteMutation.isPending}>
                            Excluir
                          </button>
                        ) : null}
                      </div>
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
