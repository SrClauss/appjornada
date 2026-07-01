// ─────────────────────────────────────────────────────────────────────────────
// Tipos alinhados ao backend FastAPI / MongoDB
// ─────────────────────────────────────────────────────────────────────────────

export type Role = 'MOTORISTA' | 'GESTOR' | 'ADMIN';
export type Situacao = 'Ativo' | 'Inativo';
export type JourneyStatus = 'ABERTA' | 'EM_ANDAMENTO' | 'EM_PAUSA' | 'ENCERRADA';
export type VehicleStatus = 'RODANDO' | 'MANUTENCAO' | 'INATIVO';
export type MaintenanceStatus = 'EM_ANDAMENTO' | 'CONCLUIDA';
export type PauseType = 'ALMOCO' | 'LANCHE' | 'DESCANSO' | 'ABASTECIMENTO' | 'PAUSA_MOTORISTA' | 'OUTRO';
export type GoalType = 'FATURAMENTO_DIA' | 'KM_MES' | 'HORAS_MES';
export type GoalReference = 'GERAL' | 'MOTORISTA';

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  nome: string;
  email: string;
  role: Role;
  situacao: Situacao;
}

// ── Usuário / Motorista ───────────────────────────────────────────────────────

export interface PerfilMotorista {
  cpf?: string;
  telefone?: string;
  nivel_id?: number;
  cnh?: {
    vencimento?: string;
    imagem_url?: string;
  };
  dados_bancarios?: {
    banco?: string;
    agencia?: string;
    conta?: string;
    operador?: string;
    cnpj?: string;
    empresa?: string;
  };
}

export interface User {
  id: string;
  nome: string;
  email: string;
  role: Role;
  situacao: Situacao;
  perfil_motorista?: PerfilMotorista;
}

export interface CreateUserPayload {
  nome: string;
  email: string;
  senha: string;
  role: Role;
}

export interface UpdateUserPayload {
  nome?: string;
  email?: string;
  situacao?: Situacao;
  senha?: string;
  pin?: string;
  perfil_motorista?: Partial<PerfilMotorista>;
}

// ── Veículo ───────────────────────────────────────────────────────────────────

export interface Veiculo {
  id: string;        // = placa, e.g. "TST1A23"
  marca_modelo: string;
  ano_modelo: string;
  cor: string;
  situacao: VehicleStatus;
  km_atual: number;
  vencimento_ipva?: string;
  imagem_clrv_url?: string;
  foto_veiculo_url?: string;
}

export interface CreateVeiculoPayload {
  id: string;
  marca_modelo: string;
  ano_modelo: string;
  cor: string;
  situacao?: VehicleStatus;
  km_atual?: number;
  vencimento_ipva?: string;
  foto_veiculo_url?: string;
}

export interface UpdateVeiculoPayload {
  marca_modelo?: string;
  ano_modelo?: string;
  cor?: string;
  situacao?: VehicleStatus;
  km_atual?: number;
  vencimento_ipva?: string;
  foto_veiculo_url?: string;
}

// ── Jornada ───────────────────────────────────────────────────────────────────

export interface Pausa {
  id: string;
  tipo: PauseType;
  inicio: string;
  fim?: string;
  duracao_segundos?: number;
}

export interface AbastecimentoJornada {
  id: string;
  hora_inicio: string;
  hora_fim?: string;
  km?: number;
  gnv?: number;
  gasolina?: number;
  etanol?: number;
  foto?: string;
}

export interface Jornada {
  id: string;
  data: string;
  motorista_id: string;
  motorista_nome?: string;
  veiculo_id: string;
  status: JourneyStatus;
  km: {
    inicial?: number;
    final?: number;
    rodados?: number;
    morta?: number;
  };
  horario: {
    inicio?: string;
    fim?: string;
    total_horas_segundos?: number;
  };
  faturamento: {
    uber?: number;
    noventa_nove?: number;
    outros?: number;
    total_dia?: number;
  };
  saldo_horas_dia?: number;
  bonus_dia?: number;
  pausas: Pausa[];
  abastecimentos: AbastecimentoJornada[];
  observacoes?: string;
}

// ── Manutenção ────────────────────────────────────────────────────────────────

export interface Manutencao {
  id: string;
  jornada_id?: string;
  motorista_id?: string;
  veiculo_id: string;
  entrada?: string;
  saida?: string;
  duracao_minutos?: number;
  km?: number;
  km_proxima_revisao?: number;
  status: MaintenanceStatus;
  oficina?: string;
  servico?: {
    tipo?: string;
    descricao?: string;
    valor?: number;
    foto_nf_url?: string;
  };
}

export interface CreateManutencaoPayload {
  veiculo_id: string;
  motorista_id?: string;
  oficina?: string;
  km?: number;
  km_proxima_revisao?: number;
  servico?: {
    tipo?: string;
    descricao?: string;
    valor?: number;
  };
}

// ── Meta & Bônus ──────────────────────────────────────────────────────────────

export interface MetaBonus {
  id: string;
  tipo: GoalType;
  referencia: GoalReference;
  faixa_minima: number;
  faixa_maxima: number;
  bonus: number;
  hora_inicio?: string;
  hora_fim?: string;
}

export interface CreateMetaPayload {
  tipo: GoalType;
  referencia: GoalReference;
  faixa_minima: number;
  faixa_maxima: number;
  bonus: number;
  hora_inicio?: string;
  hora_fim?: string;
}

// ── GPS Alerta ────────────────────────────────────────────────────────────────

export interface AlertaInatividade {
  motorista_id: string;
  motorista_nome?: string;
  jornada_id: string;
  ultima_posicao?: string;
  minutos_parado: number;
  timestamp: string;
}

// ── Relatório ─────────────────────────────────────────────────────────────────

export interface ComparativoItem {
  motorista_nome?: string;
  motorista_id?: string;
  data: string;
  km_jornada?: number;
  km_99?: number;
  km_uber?: number;
  delta_km_pct?: number;
  faturamento_declarado?: number;
  faturamento_plataforma?: number;
  delta_fat_pct?: number;
  inconsistencia: boolean;
}

// ── Paginação ─────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

// ── Legados (mantidos para compatibilidade, não usados nas views do painel) ───

/** @deprecated Usar User */
export type DriverRole = Role;
/** @deprecated Usar Situacao */
export type DriverStatus = 'ATIVO' | 'INATIVO';

export interface Driver {
  id: string;
  name: string;
  email: string;
  cpf: string;
  phone: string;
  role: DriverRole;
  status: DriverStatus;
  level: number;
  avatar?: string;
  cnh: {
    number: string;
    expiration: string;
  };
  bankAccount: {
    bank: string;
    agency: string;
    account: string;
  };
  monthlyHours: number;
  weeklyBonus: number;
  monthlyBonus: number;
  hasJourneyToday: boolean;
}

export interface Vehicle {
  id: string;
  plate: string;
  brand: string;
  model: string;
  year: number;
  color: string;
  status: VehicleStatus;
  currentKm: number;
  nextIpva: string;
  nextRevision: number;
  image?: string;
}

export interface Journey {
  id: string;
  date: string;
  driverId: string;
  vehicleId: string;
  startTime: string;
  endTime?: string;
  status: JourneyStatus;
  kmInitial: number;
  kmFinal?: number;
  kmRidden: number;
  kmDead: number;
  revenueUber: number;
  revenue99: number;
  revenueOther: number;
  revenueTotal: number;
  hours: number;
  pauses: Pause[];
  refueling: Refueling[];
  incidents: Incident[];
  startLocation?: {
    lat: number;
    lng: number;
  };
  endLocation?: {
    lat: number;
    lng: number;
  };
}

export interface Pause {
  id: string;
  type: PauseType;
  startTime: string;
  endTime: string;
  durationMinutes: number;
}

export interface Refueling {
  id: string;
  time: string;
  km: number;
  gnv: number;
  gasoline: number;
  ethanol: number;
  total: number;
}

export interface Incident {
  id: string;
  type: string;
  time: string;
  description: string;
}

export interface GpsAlert {
  id: string;
  driverId: string;
  journeyId: string;
  lastLocation: string;
  stoppedMinutes: number;
  timestamp: string;
}

export interface Goal {
  id: string;
  type: GoalType;
  reference: GoalReference;
  driverId?: string;
  minValue: number;
  maxValue: number;
  bonusValue: number;
  active: boolean;
}

export interface Maintenance {
  id: string;
  vehicleId: string;
  driverId: string;
  entryDate: string;
  workshop: string;
  service: string;
  cost: number;
  status: MaintenanceStatus;
  km: number;
  nextRevisionKm: number;
}

export interface DashboardKPI {
  activeDrivers: number;
  totalKmToday: number;
  revenueToday: number;
  revenueYesterday: number;
  activeAlerts: number;
}

export interface RefuelingRecord {
  id: string;
  journeyId: string;
  driverId: string;
  vehicleId: string;
  date: string;
  time: string;
  km: number;
  gnv: number;
  gasoline: number;
  ethanol: number;
  total: number;
  station: string;
  receipt?: string;
}

export interface Report {
  id: string;
  type: 'COMPARATIVO' | 'DESEMPENHO' | 'FINANCEIRO';
  month: string;
  driverId?: string;
  kmDeclared: number;
  km99: number;
  kmDelta: number;
  revenueDeclared: number;
  revenuePlatforms: number;
  revenueDelta: number;
  hasInconsistency: boolean;
}

export interface PerformanceMetrics {
  driverId: string;
  hours: number;
  km: number;
  revenue: number;
  punctuality: number;
  incidents: number;
  score: number;
  rank: number;
}

export interface AppSettings {
  companyName: string;
  companyLogo?: string;
  monthlyHoursGoal: number;
  weeklyHoursGoal: number;
  dailyHoursGoal: number;
  alertThresholds: {
    gpsInactivityMinutes: number;
    cnhExpirationDays: number;
    ipvaExpirationDays: number;
    revisionKmWarning: number;
  };
  notifications: {
    email: boolean;
    sms: boolean;
    push: boolean;
  };
  csvFormat: {
    separator: string;
    encoding: string;
  };
}
