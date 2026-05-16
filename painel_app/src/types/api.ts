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
}

export interface Abastecimento {
  id: string
  km?: number
  valor_gnv?: number
  valor_gasolina?: number
  valor_etanol?: number
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
}
