import 'package:flutter/material.dart';
import 'package:app_motorista/core/api_service.dart';
import 'package:app_motorista/core/fluent_theme.dart';

class MetasDashboardScreen extends StatefulWidget {
  final String motoristaId;

  const MetasDashboardScreen({
    super.key,
    required this.motoristaId,
  });

  @override
  State<MetasDashboardScreen> createState() => _MetasDashboardScreenState();
}

class _MetasDashboardScreenState extends State<MetasDashboardScreen> {
  bool _loading = true;
  Map<String, dynamic>? _dadosMetas;

  @override
  void initState() {
    super.initState();
    _carregarDados();
  }

  Future<void> _carregarDados() async {
    setState(() => _loading = true);
    final data = await ApiService.getProgressoMetas(widget.motoristaId);
    if (mounted) {
      setState(() {
        _dadosMetas = data;
        _loading = false;
      });
    }
  }

  String _formatCurrency(dynamic val) {
    if (val == null) return 'R\$ 0,00';
    final num v = (val is num) ? val : double.tryParse(val.toString()) ?? 0;
    return 'R\$ ${v.toStringAsFixed(2).replaceAll('.', ',')}';
  }

  @override
  Widget build(BuildContext context) {
    final acumulado = _dadosMetas?['acumulado_mes'] ?? {};
    final metas = (_dadosMetas?['metas'] as List<dynamic>?) ?? [];

    return Scaffold(
      backgroundColor: FluentColors.background,
      appBar: AppBar(
        title: const Text(
          'Metas & Evolução',
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
        ),
        backgroundColor: const Color(0xFF0F172A),
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: FluentColors.primaryTeal),
            onPressed: _carregarDados,
          )
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: FluentColors.primaryTeal))
          : RefreshIndicator(
              onRefresh: _carregarDados,
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header Card: Acumulado do Mês
                    _buildAcumuladoCard(acumulado),
                    const SizedBox(height: 24),

                    // Título Seção Metas
                    Row(
                      children: const [
                        Icon(Icons.flag, color: Colors.amber, size: 24),
                        SizedBox(width: 8),
                        Text(
                          'Acompanhamento de Metas',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    if (metas.isEmpty)
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Center(
                          child: Text(
                            'Nenhuma meta configurada no momento.',
                            style: TextStyle(color: FluentColors.textSecondary),
                          ),
                        ),
                      )
                    else
                      ...metas.map((m) => _buildMetaProgressCard(m)).toList(),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildAcumuladoCard(Map<String, dynamic> acumulado) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1E293B), Color(0xFF334155)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.3),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Acumulado do Mês',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: Colors.amber,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.amber.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  acumulado['mes'] ?? 'Mês Atual',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: Colors.amber,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            _formatCurrency(acumulado['total_faturamento']),
            style: const TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 16),

          // Grid de KPIs Mensais
          Row(
            children: [
              Expanded(
                child: _buildMiniKpi(
                  'R\$ / KM Global',
                  'R\$ ${(acumulado['faturamento_km_global'] ?? 0).toStringAsFixed(2)}',
                  Icons.directions_car,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildMiniKpi(
                  'R\$ / KM Útil',
                  'R\$ ${(acumulado['faturamento_km_util'] ?? 0).toStringAsFixed(2)}',
                  Icons.speed,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _buildMiniKpi(
                  'Ticket Médio',
                  _formatCurrency(acumulado['ticket_medio']),
                  Icons.receipt_long,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _buildMiniKpi(
                  'Horas Trabalhadas',
                  '${acumulado['total_horas_trabalhadas'] ?? 0}h',
                  Icons.timer,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMiniKpi(String label, String value, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A).withOpacity(0.6),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Icon(icon, size: 18, color: FluentColors.textSecondary),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(fontSize: 10, color: FluentColors.textSecondary),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          )
        ],
      ),
    );
  }

  Widget _buildMetaProgressCard(Map<String, dynamic> meta) {
    final String descricao = meta['descricao'] ?? 'Meta';
    final double pct = (meta['progresso_pct'] ?? 0.0).toDouble();
    final bool atingida = meta['atingida'] ?? false;
    final dynamic actual = meta['valor_atual'];
    final dynamic target = meta['meta_alvo'];
    final String tipo = meta['tipo'] ?? '';

    String formatVal(dynamic v) {
      if (v == null) return '0';
      if (tipo.contains('FATURAMENTO') || tipo.contains('TICKET')) {
        return _formatCurrency(v);
      }
      if (tipo.contains('KM')) {
        return 'R\$ ${(v is num ? v : double.tryParse(v.toString()) ?? 0).toStringAsFixed(2)}/km';
      }
      if (tipo.contains('HORAS')) {
        return '${v}h';
      }
      return v.toString();
    }

    final color = atingida
        ? Colors.greenAccent
        : (pct >= 70 ? Colors.amber : const Color(0xFF38BDF8));

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: atingida ? Colors.greenAccent.withOpacity(0.5) : Colors.transparent,
          width: 1.5,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Text(
                  descricao,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
              if (atingida)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.green.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: const [
                      Icon(Icons.check_circle, size: 14, color: Colors.greenAccent),
                      SizedBox(width: 4),
                      Text(
                        'Concluída',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: Colors.greenAccent,
                        ),
                      ),
                    ],
                  ),
                )
              else
                Text(
                  '${pct.toStringAsFixed(1)}%',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),

          // Progresso Texto
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Atual: ${formatVal(actual)}',
                style: const TextStyle(fontSize: 12, color: FluentColors.textSecondary),
              ),
              Text(
                'Meta: ${formatVal(target)}',
                style: const TextStyle(fontSize: 12, color: FluentColors.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Barra de Progresso
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: (pct / 100.0).clamp(0.0, 1.0),
              minHeight: 8,
              backgroundColor: const Color(0xFF0F172A),
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
        ],
      ),
    );
  }
}
