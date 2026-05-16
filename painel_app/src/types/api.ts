export type Role = 'MOTORISTA' | 'GESTOR' | 'ADMIN'

export interface Cnh {
  vencimento?: string
}

export interface DadosBancarios {
  banco?: string
  agencia?: string
  conta?: string
  cnpj?: string
}

export interface PerfilMotorista {
  cpf?: string
  telefone?: string
  cnh?: Cnh
  dados_bancarios?: DadosBancarios
}

export interface UserPublic {
  id: string
  nome: string
  email: string
  role: Role
  situacao: string
  perfil_motorista?: PerfilMotorista
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface Localizacao {
  lat: number
  lon: number
}

export interface HorarioJornada {
  inicio?: string
  fim?: string
  total_horas_segundos?: number
}

export interface KmJornada {
  inicial?: number
  final?: number
  rodados?: number
  morta?: number
}

export interface Faturamento {
  uber?: number
  noventa_nove?: number
  outros?: number
  total_dia?: number
  comprovante_uber_url?: string
  comprovante_99_url?: string
  comprovante_outros_url?: string
}

export interface Pausa {
  id: string
  tipo?: string
  inicio?: string
  fim?: string
  duracao_segundos?: number
  localizacao_inicio?: Localizacao
  localizacao_fim?: Localizacao
}

export interface Abastecimento {
  id: string
  hora_inicio?: string
  hora_fim?: string
  duracao_segundos?: number
  km?: number
  localizacao?: Localizacao
  valor_gnv?: number
  valor_gasolina?: number
  valor_etanol?: number
  foto_comprovante_url?: string
}

export interface Jornada {
  id: string
  data?: string
  motorista_id: string
  veiculo_id: string
  status: 'ABERTA' | 'EM_ANDAMENTO' | 'EM_PAUSA' | 'ENCERRADA' | string
  horario?: HorarioJornada
  km?: KmJornada
  faturamento?: Faturamento
  localizacao_inicial?: Localizacao
  localizacao_final?: Localizacao
  pausas?: Pausa[]
  abastecimentos?: Abastecimento[]
  bonus_acumulado_mes?: number
  saldo_horas_dia?: number
  observacoes?: string
}

export interface Veiculo {
  id: string
  id_placa: string
  marca_modelo?: string
  ano_modelo?: string
  cor?: string
  situacao: string
  km_atual?: number
  vencimento_ipva?: string
  imagem_clrv_url?: string
}

export interface ServicoManutencao {
  tipo?: string
  descricao?: string
  valor?: number
  foto_nf_url?: string
}

export interface Manutencao {
  id: string
  jornada_id?: string
  motorista_id?: string
  veiculo_id: string
  entrada?: string
  saida?: string
  duracao_minutos?: number
  localizacao?: Localizacao
  decisao?: string
  km?: number
  km_proxima_revisao?: number
  status: string
  oficina?: string
  servico?: ServicoManutencao
}

export interface MetaBonus {
  id: string
  tipo: string
  referencia: string
  faixa_minima?: number
  faixa_maxima?: number
  bonus?: number
}

export interface CorridaForaJornada {
  plataforma: string
  id_corrida: string
  inicio: string
  fim?: string
  origem: string
  destino: string
  valor: number
  motivo: string
}

export interface ComparativoMotorista {
  motorista_nome: string
  data: string
  jornada_km_rodados?: number
  km_plataformas_99: number
  km_plataformas_uber?: number
  delta_km_99?: number
  faturamento_uber_declarado: number
  faturamento_99_declarado: number
  faturamento_uber_relatorio: number
  faturamento_99_relatorio: number
  delta_uber: number
  delta_99: number
  total_corridas_uber: number
  total_corridas_99: number
  corridas_fora_jornada: CorridaForaJornada[]
  horas_trabalhadas?: number
  status_jornada?: string
  alertas: string[]
}

export interface ComparativoResponse {
  data: string
  total_motoristas: number
  motoristas: ComparativoMotorista[]
}

export interface RelatorioImportacaoResponse {
  importadas: number
}
