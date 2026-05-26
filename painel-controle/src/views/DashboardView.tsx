import { KPICard } from '@/components/KPICard';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Users, Car, CurrencyDollar, Warning } from '@phosphor-icons/react';
import { useDashboard } from '@/hooks/useDashboard';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend,
} from 'recharts';

const formatCurrency = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const DAY_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];
const WEEK_DAYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'];

export function DashboardView() {
  const { isLoading, kpis } = useDashboard();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          icon={<Users size={24} className="text-success" />}
          label="Motoristas em Jornada Hoje"
          value={kpis.motoristasAtivos}
          status="success"
        />
        <KPICard
          icon={<Car size={24} className="text-accent" />}
          label="Km Rodados Hoje (frota total)"
          value={kpis.totalKmHoje}
          status="default"
        />
        <KPICard
          icon={<CurrencyDollar size={24} className="text-accent" />}
          label="Faturamento do Dia"
          value={formatCurrency(kpis.faturamentoHoje)}
          status="default"
        />
        <KPICard
          icon={<Warning size={24} className="text-destructive" />}
          label="Alertas GPS Ativos"
          value={kpis.totalAlertas}
          status={kpis.totalAlertas > 0 ? 'danger' : 'success'}
        />
      </div>

      {/* Gráficos principais */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bar Chart — Faturamento semanal por motorista */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Faturamento por Motorista — Semana Atual</h3>
          {kpis.weeklyRevenueByDriver.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Nenhuma jornada registrada esta semana.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={kpis.weeklyRevenueByDriver}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `R$${v}`} />
                <Tooltip formatter={(v) => formatCurrency(Number(v))} />
                <Legend />
                {WEEK_DAYS.map((day, idx) => (
                  <Bar key={day} dataKey={day} fill={DAY_COLORS[idx % DAY_COLORS.length]} name={day} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Line Chart — Horas acumuladas vs. meta CLT */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Horas Trabalhadas vs. Meta CLT — Mês Atual</h3>
          {kpis.horasData.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Nenhuma jornada registrada este mês.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={kpis.horasData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="day"
                  tick={{ fontSize: 12 }}
                  label={{ value: 'Dia do Mês', position: 'insideBottom', offset: -5 }}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => `${v}h`} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="hours"
                  stroke="#3b82f6"
                  name="Horas Acumuladas"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="meta"
                  stroke="#f59e0b"
                  strokeDasharray="5 5"
                  name="Meta CLT (220h)"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* Status jornadas + Alertas GPS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Status das Jornadas Hoje</h3>
          {kpis.jornadasStatus.every((j) => j.value === 0) ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Nenhuma jornada registrada hoje.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={kpis.jornadasStatus.filter((j) => j.value > 0)}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                  label={(entry) => `${entry.name}: ${entry.value}`}
                >
                  {kpis.jornadasStatus.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Alertas de Inatividade GPS</h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Motorista</TableHead>
                <TableHead>Última Localização</TableHead>
                <TableHead>Parado há</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {kpis.alertas.length > 0 ? (
                kpis.alertas.map((alert, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">
                      {alert.motorista_nome ?? alert.motorista_id}
                    </TableCell>
                    <TableCell className="text-sm">{alert.ultima_posicao ?? '—'}</TableCell>
                    <TableCell>
                      <Badge variant="destructive">
                        PARADO {alert.minutos_parado} MIN
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                    Nenhum alerta ativo
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  );
}
