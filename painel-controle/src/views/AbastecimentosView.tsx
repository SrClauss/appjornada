import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Drop, TrendUp } from '@phosphor-icons/react';
import { useJornadas } from '@/hooks/useJornadas';
import type { AbastecimentoJornada, Jornada } from '@/lib/types';

const formatCurrency = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

interface AbastecimentoFlat extends AbastecimentoJornada {
  motorista_nome: string;
  veiculo_id: string;
  data: string;
}

export function AbastecimentosView() {
  const [search, setSearch] = useState('');

  // Abastecimentos são embutidos nas jornadas (não há endpoint próprio)
  const { data: jornadas = [], isLoading } = useJornadas({ size: 200 });

  // Extrai e aplana todos os abastecimentos de todas as jornadas
  const abastecimentos: AbastecimentoFlat[] = jornadas.flatMap((j: Jornada) =>
    (j.abastecimentos ?? []).map((ab) => ({
      ...ab,
      motorista_nome: j.motorista_nome ?? j.motorista_id,
      veiculo_id: j.veiculo_id,
      data: j.data,
    })),
  );

  const filtered = abastecimentos.filter((ab) => {
    const q = search.toLowerCase();
    return (
      ab.motorista_nome.toLowerCase().includes(q) ||
      ab.veiculo_id.toLowerCase().includes(q)
    );
  });

  const totalGnv       = abastecimentos.reduce((s, a) => s + (a.gnv ?? 0), 0);
  const totalGasolina  = abastecimentos.reduce((s, a) => s + (a.gasolina ?? 0), 0);
  const totalEtanol    = abastecimentos.reduce((s, a) => s + (a.etanol ?? 0), 0);
  const totalCusto     = totalGnv + totalGasolina + totalEtanol;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-foreground">Abastecimentos</h1>
        <p className="text-muted-foreground mt-1">Controle de abastecimentos da frota</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-accent/10 rounded-lg">
                <Drop className="text-accent" size={24} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total GNV</p>
                <p className="text-2xl font-semibold">{formatCurrency(totalGnv)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-warning/10 rounded-lg">
                <Drop className="text-warning" size={24} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Gasolina</p>
                <p className="text-2xl font-semibold">{formatCurrency(totalGasolina)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-success/10 rounded-lg">
                <Drop className="text-success" size={24} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Etanol</p>
                <p className="text-2xl font-semibold">{formatCurrency(totalEtanol)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-primary/10 rounded-lg">
                <TrendUp className="text-primary" size={24} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Custo Total</p>
                <p className="text-2xl font-semibold">{formatCurrency(totalCusto)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col md:flex-row justify-between gap-4">
            <CardTitle>Histórico de Abastecimentos</CardTitle>
            <Input
              placeholder="Buscar por motorista ou veículo..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full md:w-72"
            />
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Data</TableHead>
                    <TableHead>Hora Início</TableHead>
                    <TableHead>Motorista</TableHead>
                    <TableHead>Veículo</TableHead>
                    <TableHead>Km</TableHead>
                    <TableHead>GNV (R$)</TableHead>
                    <TableHead>Gasolina (R$)</TableHead>
                    <TableHead>Etanol (R$)</TableHead>
                    <TableHead>Foto</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                        Nenhum abastecimento registrado.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filtered.map((ab) => (
                      <TableRow key={ab.id}>
                        <TableCell>
                          {new Date(ab.data).toLocaleDateString('pt-BR')}
                        </TableCell>
                        <TableCell>{ab.hora_inicio}</TableCell>
                        <TableCell className="font-medium">{ab.motorista_nome}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{ab.veiculo_id}</Badge>
                        </TableCell>
                        <TableCell className="font-mono">
                          {ab.km?.toLocaleString('pt-BR') ?? '—'}
                        </TableCell>
                        <TableCell>{ab.gnv ? formatCurrency(ab.gnv) : '—'}</TableCell>
                        <TableCell>{ab.gasolina ? formatCurrency(ab.gasolina) : '—'}</TableCell>
                        <TableCell>{ab.etanol ? formatCurrency(ab.etanol) : '—'}</TableCell>
                        <TableCell>
                          {ab.foto ? (
                            <a
                              href={ab.foto}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-accent underline text-sm"
                            >
                              Ver foto
                            </a>
                          ) : (
                            '—'
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
