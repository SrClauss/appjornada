import 'package:flutter/material.dart';
import '../../../shared/models/jornada_model.dart';

class JornadaStatusCard extends StatelessWidget {
  final JornadaModel? jornada;

  const JornadaStatusCard({super.key, this.jornada});

  @override
  Widget build(BuildContext context) {
    if (jornada == null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Icon(Icons.info_outline,
                  color: Theme.of(context).colorScheme.secondary),
              const SizedBox(width: 12),
              const Text('Nenhuma jornada ativa'),
            ],
          ),
        ),
      );
    }

    Color statusColor;
    String statusLabel;
    switch (jornada!.status) {
      case 'ABERTA':
      case 'EM_ANDAMENTO':
        statusColor = Colors.green;
        statusLabel = 'Em andamento';
      case 'EM_PAUSA':
        statusColor = Colors.orange;
        statusLabel = 'Em pausa';
      default:
        statusColor = Colors.grey;
        statusLabel = jornada!.status ?? 'Desconhecido';
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: statusColor,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  statusLabel,
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const Divider(height: 24),
            _InfoRow(
              icon: Icons.attach_money,
              label: 'Faturamento',
              value:
                  'R\$ ${(jornada!.faturamento?.totalDia ?? 0).toStringAsFixed(2)}',
            ),
            const SizedBox(height: 8),
            _InfoRow(
              icon: Icons.speed,
              label: 'Km rodados',
              value:
                  '${(jornada!.km?.rodados ?? 0).toStringAsFixed(1)} km',
            ),
            const SizedBox(height: 8),
            _InfoRow(
              icon: Icons.schedule,
              label: 'Saldo de horas',
              value: _formatSaldoHoras(jornada!.saldoHorasDia),
            ),
          ],
        ),
      ),
    );
  }

  String _formatSaldoHoras(double? saldo) {
    if (saldo == null) return '—';
    final sign = saldo >= 0 ? '+' : '';
    final h = saldo.abs().truncate();
    final m = ((saldo.abs() - h) * 60).round();
    return '$sign${h}h${m.toString().padLeft(2, '0')}min';
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 18, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 8),
        Text(
          '$label: ',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
        ),
        Text(
          value,
          style: Theme.of(context)
              .textTheme
              .bodyMedium
              ?.copyWith(fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}
