import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Eye } from '@phosphor-icons/react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useJornadas } from '@/hooks/useJornadas';
import type { JourneyStatus } from '@/lib/types';

const formatCurrency = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const statusBadgeVariant = (status: JourneyStatus) => {
  if (status === 'ENCERRADA') return 'default' as const;
  if (status === 'ABERTA' || status === 'EM_ANDAMENTO') return 'secondary' as const;
  return 'outline' as const;
};

export function JornadasView() {
  const [search, setSearch] = useState('');
  const [dataFiltro, setDataFiltro] = useState('');

  const { data: jornadas = [], isLoading } = useJornadas({
    motorista_id: search || undefined,
    data: dataFiltro || undefined,
  });

  const kmByDriver = jornadas.reduce<{ name: string; km: number }[]>((acc, j) => {
    const nome = (j.motorista_nome ?? j.motorista_id).split(' ')[0];
    const existing = acc.find((d) => d.name === nome);
    if (existing) {
      existing.km += j.km?.rodados ?? 0;
    } else {
      acc.push({ name: nome, km: j.km?.rodados ?? 0 });
    }
    return acc;
  }, []).sort((a, b) => b.km - a.km);

  return (
    <div className="space-y-6">
      <div className="flex gap-4 flex-wrap">
        <Input
          placeholder="ID do motorista..."
          className="max-w-xs"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Input
          type="date"
          className="max-w-xs"
          value={dataFiltro}
          onChange={(e) => setDataFiltro(e.target.value)}
        />
        {dataFiltro && (
          <Button variant="outline" onClick={() => setDataFiltro('')}>
            Limpar filtro
          </Button>
        )}
      </div>

      {isLoading ? (
        <Skeleton className="h-80 w-full rounded-xl" />
      ) : (
        <>
          {kmByDriver.length > 0 && (
            <Card className="p-6">
              <h3 className="text-lg font-semibold mb-4">Km Rodados por Motorista</h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={kmByDriver} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 12 }} width={80} />
                  <Tooltip />
                  <Bar dataKey="km" fill="#3b82f6" name="Km Rodados" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4">Jornadas</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data</TableHead>
                  <TableHead>Motorista</TableHead>
                  <TableHead>Veículo</TableHead>
                  <TableHead>Início</TableHead>
                  <TableHead>Fim</TableHead>
                  <TableHead>Km</TableHead>
                  <TableHead>Faturamento</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jornadas.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                      Nenhuma jornada encontrada.
                    </TableCell>
                  </TableRow>
                ) : (
                  jornadas.map((j) => (
                    <TableRow key={j.id}>
                      <TableCell>{new Date(j.data).toLocaleDateString('pt-BR')}</TableCell>
                      <TableCell className="font-medium">
                        {j.motorista_nome ?? j.motorista_id}
                      </TableCell>
                      <TableCell>{j.veiculo_id}</TableCell>
                      <TableCell>{j.horario?.inicio ?? '—'}</TableCell>
                      <TableCell>{j.horario?.fim ?? '—'}</TableCell>
                      <TableCell>{j.km?.rodados ?? 0} km</TableCell>
                      <TableCell>{formatCurrency(j.faturamento?.total_dia ?? 0)}</TableCell>
                      <TableCell>
                        <Badge variant={statusBadgeVariant(j.status)}>{j.status}</Badge>
                      </TableCell>
                      <TableCell>
                        <Button size="sm" variant="ghost">
                          <Eye size={16} />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </>
      )}
    </div>
  );
}

