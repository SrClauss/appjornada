import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../../shared/models/jornada_model.dart';
import '../../../shared/models/pausa_model.dart';
import '../../../shared/models/abastecimento_model.dart';
import '../services/historico_service.dart';

class HistoricoScreen extends StatefulWidget {
  const HistoricoScreen({super.key});

  @override
  State<HistoricoScreen> createState() => _HistoricoScreenState();
}

class _HistoricoScreenState extends State<HistoricoScreen> {
  final List<JornadaModel> _jornadas = [];
  bool _isLoading = false;
  bool _hasMore = true;
  int _skip = 0;
  static const int _limit = 20;
  String? _error;

  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _load();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
            _scrollController.position.maxScrollExtent - 200 &&
        !_isLoading &&
        _hasMore) {
      _load();
    }
  }

  Future<void> _load() async {
    if (_isLoading) return;
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final items = await HistoricoService.getJornadas(
        skip: _skip,
        limit: _limit,
      );
      setState(() {
        _jornadas.addAll(items);
        _skip += items.length;
        _hasMore = items.length == _limit;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Erro ao carregar histórico.';
        _isLoading = false;
      });
    }
  }

  Future<void> _refresh() async {
    setState(() {
      _jornadas.clear();
      _skip = 0;
      _hasMore = true;
      _error = null;
    });
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Histórico de Jornadas')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: _jornadas.isEmpty && _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _jornadas.isEmpty && _error != null
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_error!,
                            style: TextStyle(
                                color: Theme.of(context).colorScheme.error)),
                        const SizedBox(height: 12),
                        TextButton(
                          onPressed: _refresh,
                          child: const Text('Tentar novamente'),
                        ),
                      ],
                    ),
                  )
                : _jornadas.isEmpty
                    ? const Center(child: Text('Nenhuma jornada registrada.'))
                    : ListView.builder(
                        controller: _scrollController,
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        itemCount: _jornadas.length + (_hasMore ? 1 : 0),
                        itemBuilder: (context, index) {
                          if (index == _jornadas.length) {
                            return const Padding(
                              padding: EdgeInsets.all(16),
                              child: Center(child: CircularProgressIndicator()),
                            );
                          }
                          return _JornadaTile(
                            jornada: _jornadas[index],
                            onTap: () => _showDetail(_jornadas[index]),
                          );
                        },
                      ),
      ),
    );
  }

  void _showDetail(JornadaModel jornada) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => _JornadaDetailSheet(jornada: jornada),
    );
  }
}

// ---------------------------------------------------------------------------
// List tile
// ---------------------------------------------------------------------------

class _JornadaTile extends StatelessWidget {
  final JornadaModel jornada;
  final VoidCallback onTap;

  const _JornadaTile({required this.jornada, required this.onTap});

  Color _statusColor(BuildContext context) {
    switch (jornada.status) {
      case 'FECHADA':
        return Colors.green;
      case 'EM_ANDAMENTO':
      case 'ABERTA':
        return Colors.blue;
      case 'EM_PAUSA':
        return Colors.orange;
      default:
        return Theme.of(context).colorScheme.outline;
    }
  }

  String _statusLabel() {
    switch (jornada.status) {
      case 'FECHADA':
        return 'Encerrada';
      case 'EM_ANDAMENTO':
      case 'ABERTA':
        return 'Em andamento';
      case 'EM_PAUSA':
        return 'Em pausa';
      default:
        return jornada.status ?? '-';
    }
  }

  @override
  Widget build(BuildContext context) {
    final fmtDate = jornada.data != null
        ? DateFormat('dd/MM/yyyy').format(DateTime.parse(jornada.data!))
        : '-';
    final km = (jornada.km?.rodados ?? 0).toStringAsFixed(1);
    final fat = 'R\$ ${(jornada.faturamento?.totalDia ?? 0).toStringAsFixed(2)}';
    final statusColor = _statusColor(context);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: ListTile(
        onTap: onTap,
        title: Row(
          children: [
            Text(fmtDate, style: const TextStyle(fontWeight: FontWeight.bold)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: statusColor.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: statusColor),
              ),
              child: Text(
                _statusLabel(),
                style: TextStyle(
                    color: statusColor,
                    fontSize: 12,
                    fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Row(
            children: [
              const Icon(Icons.speed, size: 14),
              const SizedBox(width: 4),
              Text('$km km'),
              const SizedBox(width: 16),
              const Icon(Icons.attach_money, size: 14),
              const SizedBox(width: 4),
              Text(fat),
            ],
          ),
        ),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Detail bottom sheet
// ---------------------------------------------------------------------------

class _JornadaDetailSheet extends StatelessWidget {
  final JornadaModel jornada;

  const _JornadaDetailSheet({required this.jornada});

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.7,
      maxChildSize: 0.95,
      builder: (_, scrollCtrl) => ListView(
        controller: scrollCtrl,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.outlineVariant,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          Text('Detalhes da Jornada',
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.center),
          const SizedBox(height: 16),
          _Section(title: 'Horários', children: [
            _DetailRow(label: 'Início', value: jornada.horario?.inicio ?? '-'),
            _DetailRow(label: 'Fim', value: jornada.horario?.fim ?? '-'),
            _DetailRow(
              label: 'Duração',
              value: _fmtDuration(jornada.horario?.totalHorasSegundos ?? 0),
            ),
          ]),
          const SizedBox(height: 12),
          _Section(title: 'Quilometragem', children: [
            _DetailRow(
              label: 'KM inicial',
              value: '${(jornada.km?.inicial ?? 0).toStringAsFixed(1)} km',
            ),
            _DetailRow(
              label: 'KM final',
              value: '${(jornada.km?.final_ ?? 0).toStringAsFixed(1)} km',
            ),
            _DetailRow(
              label: 'Rodados',
              value: '${(jornada.km?.rodados ?? 0).toStringAsFixed(1)} km',
            ),
          ]),
          const SizedBox(height: 12),
          _Section(title: 'Faturamento', children: [
            _DetailRow(
              label: 'Uber',
              value:
                  'R\$ ${(jornada.faturamento?.uber ?? 0).toStringAsFixed(2)}',
            ),
            _DetailRow(
              label: '99',
              value:
                  'R\$ ${(jornada.faturamento?.noventaNove ?? 0).toStringAsFixed(2)}',
            ),
            _DetailRow(
              label: 'Outros',
              value:
                  'R\$ ${(jornada.faturamento?.outros ?? 0).toStringAsFixed(2)}',
            ),
            _DetailRow(
              label: 'Total',
              value:
                  'R\$ ${(jornada.faturamento?.totalDia ?? 0).toStringAsFixed(2)}',
              bold: true,
            ),
          ]),
          if (jornada.saldoHorasDia != null) ...[
            const SizedBox(height: 12),
            _Section(title: 'Saldo de Horas CLT', children: [
              _DetailRow(
                label: 'Saldo do dia',
                value: _fmtDuration(jornada.saldoHorasDia!.round()),
                bold: true,
              ),
            ]),
          ],
          if (jornada.pausas.isNotEmpty) ...[
            const SizedBox(height: 12),
            _Section(
              title: 'Pausas (${jornada.pausas.length})',
              children: jornada.pausas.map((p) => _PausaRow(pausa: p)).toList(),
            ),
          ],
          if (jornada.abastecimentos.isNotEmpty) ...[
            const SizedBox(height: 12),
            _Section(
              title: 'Abastecimentos (${jornada.abastecimentos.length})',
              children: jornada.abastecimentos
                  .map((a) => _AbastRow(abast: a))
                  .toList(),
            ),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  String _fmtDuration(int seconds) {
    final d = Duration(seconds: seconds.abs());
    final sign = seconds < 0 ? '-' : '';
    final h = d.inHours.toString().padLeft(2, '0');
    final m = (d.inMinutes % 60).toString().padLeft(2, '0');
    return '$sign$h h $m min';
  }
}

class _Section extends StatelessWidget {
  final String title;
  final List<Widget> children;
  const _Section({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title,
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(color: Theme.of(context).colorScheme.primary)),
        const Divider(height: 8),
        ...children,
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;
  final bool bold;
  const _DetailRow({required this.label, required this.value, this.bold = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant)),
          Text(value,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(fontWeight: bold ? FontWeight.bold : null)),
        ],
      ),
    );
  }
}

class _PausaRow extends StatelessWidget {
  final PausaModel pausa;
  const _PausaRow({required this.pausa});

  String _tipoLabel(String tipo) {
    switch (tipo) {
      case 'ALMOCO':
        return 'Almoço';
      case 'ABASTECIMENTO':
        return 'Abastecimento';
      default:
        return 'Pausa livre';
    }
  }

  @override
  Widget build(BuildContext context) {
    final dur = pausa.duracaoSegundos != null
        ? '${pausa.duracaoSegundos! ~/ 60} min'
        : '-';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          const Icon(Icons.pause_circle_outline, size: 16),
          const SizedBox(width: 6),
          Expanded(child: Text(_tipoLabel(pausa.tipo))),
          Text(dur, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _AbastRow extends StatelessWidget {
  final AbastecimentoModel abast;
  const _AbastRow({required this.abast});

  @override
  Widget build(BuildContext context) {
    final valores = <String>[];
    if ((abast.valorGasolina ?? 0) > 0) {
      valores.add('Gasolina R\$ ${abast.valorGasolina!.toStringAsFixed(2)}');
    }
    if ((abast.valorGnv ?? 0) > 0) {
      valores.add('GNV R\$ ${abast.valorGnv!.toStringAsFixed(2)}');
    }
    if ((abast.valorEtanol ?? 0) > 0) {
      valores.add('Etanol R\$ ${abast.valorEtanol!.toStringAsFixed(2)}');
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          const Icon(Icons.local_gas_station, size: 16),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              '${abast.km?.toStringAsFixed(1)} km — ${valores.join(', ')}',
            ),
          ),
        ],
      ),
    );
  }
}

