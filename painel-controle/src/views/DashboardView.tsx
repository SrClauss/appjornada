import { KPICard } from '@/components/KPICard';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Users, Car, CurrencyDollar, Warning } from '@phosphor-icons/react';
import { useDashboard } from '@/hooks/useDashboard';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';

const formatCurrency = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

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
        <Skeleton className="h-80 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Faturamento por Motorista — Hoje</h3>
          {kpis.faturamentoPorMotorista.length === 0 ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Nenhuma jornada registrada hoje.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={kpis.faturamentoPorMotorista}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="nome" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => formatCurrency(Number(v))} />
                <Bar dataKey="total" fill="#3b82f6" name="Faturamento" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Status das Jornadas Hoje</h3>
          {kpis.jornadasStatus.every((j) => j.value === 0) ? (
            <p className="text-muted-foreground text-sm py-8 text-center">
              Nenhuma jornada registrada hoje.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
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
      </div>

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
  );
}

