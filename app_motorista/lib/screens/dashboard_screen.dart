import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:app_motorista/core/api_service.dart';
import 'package:app_motorista/core/overlay_service.dart';
import 'package:app_motorista/widgets/abastecimento_modal.dart';

import 'package:app_motorista/widgets/manutencao_dialog.dart';
import 'package:app_motorista/widgets/sinistro_modal.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import 'package:app_motorista/screens/metas_dashboard_screen.dart';
import 'package:app_motorista/core/fluent_theme.dart';
import 'package:app_motorista/core/gps_service.dart';

class DashboardScreen extends StatefulWidget {
  final Map<String, dynamic> jornada;
  final Function(String, Map<String, dynamic>?) onAction;
  final VoidCallback onLogout;

  const DashboardScreen({
    super.key,
    required this.jornada,
    required this.onAction,
    required this.onLogout,
  });

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Timer? _timer;
  Duration _elapsedJornada = const Duration(hours: 0, minutes: 0, seconds: 0);
  final Duration _metaCLT = const Duration(hours: 8, minutes: 48, seconds: 0);
  bool _isWeekendOrHoliday = false;
  bool _loading = false;
  Map<String, dynamic>? _metricasJornada;

  @override
  void initState() {
    super.initState();
    _checkWeekendOrHoliday();
    _startTimer();
    _carregarMetricas();
  }

  Future<void> _carregarMetricas() async {
    final jId = widget.jornada['_id'] ?? widget.jornada['id'];
    if (jId != null) {
      final res = await ApiService.getMetricasJornada(jId.toString());
      if (mounted && res != null) {
        setState(() {
          _metricasJornada = res;
        });
      }
    }
  }

  void _checkWeekendOrHoliday() {
    // Sábado (6) ou Domingo (7) ou feriados
    final now = DateTime.now();
    setState(() {
      _isWeekendOrHoliday = now.weekday == DateTime.saturday || now.weekday == DateTime.sunday;
    });
  }

  void _startTimer() {
    // Pega hora inicial da jornada
    final inicioStr = widget.jornada['horario']['inicio'];
    if (inicioStr != null) {
      final now = DateTime.now();
      final dataStr = widget.jornada['data'] ??
          '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      
      final utcIsoStr = '${dataStr}T${inicioStr}Z';
      final inicioDt = DateTime.parse(utcIsoStr).toLocal();

      _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
        final diff = DateTime.now().difference(inicioDt);
        setState(() {
          _elapsedJornada = diff;
        });
      });
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  String _formatDuration(Duration d) {
    final h = d.inHours.toString().padLeft(2, '0');
    final m = (d.inMinutes % 60).toString().padLeft(2, '0');
    final s = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$h:$m:$s';
  }

  String _formatTimer() {
    return _formatDuration(_elapsedJornada);
  }

  String _getSubtitleText() {
    if (_isWeekendOrHoliday) {
      return 'Final de semana / Feriado (100% Extra)';
    }
    if (_elapsedJornada < _metaCLT) {
      final rest = _metaCLT - _elapsedJornada;
      return 'Faltam ${_formatDuration(rest)} para a meta de 08:48h';
    } else {
      final extra = _elapsedJornada - _metaCLT;
      return 'Meta cumprida! Horas extras: ${_formatDuration(extra)}';
    }
  }

  Color _getTimerColor() {
    if (_isWeekendOrHoliday) return Colors.greenAccent;
    if (_elapsedJornada < _metaCLT) return Colors.orangeAccent;
    return Colors.greenAccent;
  }

  void _confirmarEIniciarPausa() {
    if (_loading) return;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Row(
          children: [
            Icon(Icons.pause_circle_outline, color: Colors.amber, size: 28),
            SizedBox(width: 10),
            Text('Pausar Jornada?', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
          ],
        ),
        content: const Text(
          'Deseja realmente iniciar a sua pausa (descanso/almoço) agora?',
          style: TextStyle(color: Colors.white70, fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('CANCELAR', style: TextStyle(color: Colors.grey, fontWeight: FontWeight.bold)),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.amber[800],
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            onPressed: () {
              Navigator.pop(context);
              _iniciarPausa();
            },
            child: const Text('CONFIRMAR PAUSA', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Future<void> _iniciarPausa() async {
    if (_loading) return;
    setState(() {
      _loading = true;
    });
    try {
      double lat = -20.219;
      double lon = -40.264;
      try {
        final pos = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 4),
        );
        lat = pos.latitude;
        lon = pos.longitude;
      } catch (_) {}

      final jId = widget.jornada['_id'] ?? widget.jornada['id'];
      final res = await http.post(
        Uri.parse('${ApiService.baseUrl}/jornadas/$jId/pausas?tipo=PAUSA_MOTORISTA&localizacao_lat=$lat&localizacao_lon=$lon'),
        headers: ApiService.headers,
      );
      if (res.statusCode == 201) {
        final body = json.decode(res.body);
        widget.onAction('pause', body);
      }
    } catch (_) {
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  void _abrirAbastecimento() {
    if (_loading) return;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F172A),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) => AbastecimentoModal(jornada: widget.jornada),
    );
  }

  void _abrirManutencao() {
    if (_loading) return;
    showDialog(
      context: context,
      builder: (context) => ManutencaoDialog(
        jornada: widget.jornada,
        onCompleted: (action, updatedJornada) {
          Navigator.pop(context);
          if (action == 'pause') {
            widget.onAction('manutencao_rapida', updatedJornada);
          } else if (action == 'close') {
            widget.onAction('close', null);
          }
        },
      ),
    );
  }

  void _abrirSinistro() {
    if (_loading) return;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F172A),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) => SinistroModal(jornada: widget.jornada),
    );
  }

  Future<void> _enviarPrint() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery);
    if (picked != null) {
      widget.onAction('processar_print', {'path': picked.path});
    }
  }

  Future<void> _encerrarJornada() async {
    setState(() => _loading = true);
    final jId = widget.jornada['_id'] ?? widget.jornada['id'];
    final ok = await ApiService.iniciarPreFechamento(jId);
    setState(() => _loading = false);
    if (ok) {
      GpsService.stopTracking();
      widget.onAction('close_wizard', null);
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Erro ao iniciar fechamento. Tente novamente.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Painel do Motorista'),
        backgroundColor: const Color(0xFF1E293B),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: widget.onLogout,
          )
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: EdgeInsets.only(
            top: 24.0,
            left: 24.0,
            right: 24.0,
            bottom: MediaQuery.of(context).padding.bottom + 64.0,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
            // CARD CRONÔMETRO
            Card(
              elevation: 4,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF1E293B), Color(0xFF0F172A)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  children: [
                    Text(
                      'STATUS DA JORNADA: ATIVA',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, letterSpacing: 1.5, color: Colors.blueAccent),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      _formatTimer(),
                      style: TextStyle(
                        fontSize: 48,
                        fontWeight: FontWeight.bold,
                        fontFamily: 'monospace',
                        color: _getTimerColor(),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _getSubtitleText(),
                      style: const TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 24),
            // PAINEL DE FATURAMENTO DA JORNADA
            _buildFaturamentoPanel(),

            const SizedBox(height: 20),
            // CARDS DE MÉTRICAS DA JORNADA (Fat/KM Global, Fat/KM Útil, Ticket Médio)
            _buildMetricasOperacionaisCard(),

            const SizedBox(height: 24),
            // CARDS ACUMULADOS
            Row(
              children: [
                Expanded(
                  child: _buildMetricCard(
                    title: 'Horas Líquidas',
                    value: _isWeekendOrHoliday
                        ? '${_elapsedJornada.inHours}h ${(_elapsedJornada.inMinutes % 60)}m'
                        : '${_elapsedJornada.inHours}h / 08h 48m',
                    icon: Icons.hourglass_bottom,
                    color: Colors.indigo,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: _buildMetricCard(
                    title: 'Faturamento Particular',
                    value: () {
                      final pFat = double.tryParse('${widget.jornada['faturamento']?['corridas_particulares']}') ??
                          double.tryParse('${widget.jornada['faturamento']?['outros']}') ??
                          double.tryParse('${widget.jornada['faturamento']?['particular']}') ?? 0.0;
                      if (pFat > 0) {
                        return 'R\$ ${pFat.toStringAsFixed(2).replaceAll('.', ',')}';
                      }
                      return 'R\$ 0,00';
                    }(),             
                    icon: Icons.monetization_on,
                    color: const Color(0xFF10B981),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 32),
            const Text(
              'Ações Operacionais (Rotina)',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 16),

            // CARD HERO EM DESTAQUE: CORRIDA PARTICULAR
            Card(
              elevation: 8,
              shadowColor: const Color(0xFF34D399).withOpacity(0.3),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(20),
                side: BorderSide(color: const Color(0xFF34D399).withOpacity(0.5), width: 1.5),
              ),
              child: InkWell(
                onTap: () {
                  widget.onAction('corrida_particular', null);
                },
                borderRadius: BorderRadius.circular(20),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF064E3B), Color(0xFF022C22), Color(0xFF0F172A)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: const Color(0xFF34D399).withOpacity(0.15),
                              shape: BoxShape.circle,
                              border: Border.all(color: const Color(0xFF34D399).withOpacity(0.4)),
                            ),
                            child: const Icon(Icons.directions_car_filled_rounded, color: Color(0xFF34D399), size: 30),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            decoration: BoxDecoration(
                              color: const Color(0xFF34D399).withOpacity(0.2),
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(color: const Color(0xFF34D399)),
                            ),
                            child: const Row(
                              children: [
                                Icon(Icons.flash_on, color: Color(0xFF34D399), size: 14),
                                SizedBox(width: 4),
                                Text(
                                  'LANÇAMENTO AO VIVO',
                                  style: TextStyle(color: Color(0xFF34D399), fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 0.8),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'CORRIDA PARTICULAR',
                        style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Gerencie, calcule e lance valores de corridas particulares fora dos aplicativos em tempo real.',
                        style: TextStyle(color: Colors.grey[300], fontSize: 13, height: 1.3),
                      ),
                      const SizedBox(height: 18),
                      Container(
                        width: double.infinity,
                        height: 46,
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.add_circle_outline, color: Colors.white),
                            SizedBox(width: 8),
                            Text(
                              'INICIAR OU REGISTRAR VIAGEM',
                              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            const SizedBox(height: 16),
            _buildActionButton(
              title: 'ABASTECIMENTO',
              subtitle: 'Registre combustível e audite deslocamentos',
              icon: Icons.local_gas_station,
              color: Colors.indigo,
              onPressed: _abrirAbastecimento,
            ),
            const SizedBox(height: 16),
            _buildActionButton(
              title: 'INICIAR PAUSA',
              subtitle: 'Almoço, descanso ou lanche',
              icon: Icons.pause_circle_outline,
              color: Colors.amber,
              onPressed: _confirmarEIniciarPausa,
            ),
            const SizedBox(height: 16),
            _buildActionButton(
              title: 'MANUTENÇÃO',
              subtitle: 'Entrada em oficina ou preventiva',
              icon: Icons.build,
              color: Colors.amber[800]!,
              onPressed: _abrirManutencao,
            ),
            const SizedBox(height: 16),
            _buildActionButton(
              title: 'REGISTRAR SINISTRO',
              subtitle: 'Colisão, avaria, guincho ou acidente',
              icon: Icons.warning_amber_rounded,
              color: Colors.redAccent,
              onPressed: _abrirSinistro,
            ),
            const SizedBox(height: 24),
            
            // DADOS DE VISTORIA E FOTOS DO CHECK-IN
            _buildCheckInInfo(),
            
            const SizedBox(height: 40),
            // ENCERRAR JORNADA
            SizedBox(
              width: double.infinity,
              height: 56,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.red,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                ),
                onPressed: _encerrarJornada,
                icon: const Icon(Icons.power_settings_new, color: Colors.white),
                label: const Text('ENCERRAR JORNADA HOJE', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

  String _getFullUrl(String? url) {
    if (url == null) return '';
    if (url.startsWith('http')) return url;
    final base = ApiService.baseUrl.replaceAll('/api', '');
    return '$base$url';
  }

  void _mostrarImagemZoom(String url, String title) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        child: Container(
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(16),
          ),
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(
                  url,
                  fit: BoxFit.contain,
                  errorBuilder: (ctx, err, stack) => const Center(
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 32.0),
                      child: Column(
                        children: [
                          Icon(Icons.broken_image, color: Colors.redAccent, size: 48),
                          SizedBox(height: 8),
                          Text('Erro ao carregar imagem', style: TextStyle(color: Colors.grey)),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMetricasOperacionaisCard() {
    final double fatKmGlobal = (_metricasJornada?['faturamento_km_global'] as num?)?.toDouble() ?? 0.0;
    final double fatKmUtil = (_metricasJornada?['faturamento_km_util'] as num?)?.toDouble() ?? 0.0;
    final double ticketMedio = (_metricasJornada?['ticket_medio'] as num?)?.toDouble() ?? 0.0;
    final int totalCorridas = (_metricasJornada?['total_corridas'] as num?)?.toInt() ?? 0;

    final motoristaId = widget.jornada['motorista_id']?.toString() ?? ApiService.motoristaId ?? '';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: const [
                  Icon(Icons.analytics, color: Colors.amber, size: 20),
                  SizedBox(width: 8),
                  Text(
                    'Métricas da Jornada',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
              InkWell(
                onTap: () {
                  if (motoristaId.isNotEmpty) {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => MetasDashboardScreen(motoristaId: motoristaId),
                      ),
                    );
                  }
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.amber.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: const [
                      Text(
                        'Ver Metas',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Colors.amber,
                        ),
                      ),
                      SizedBox(width: 4),
                      Icon(Icons.arrow_forward_ios, size: 10, color: Colors.amber),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          Row(
            children: [
              Expanded(
                child: _buildItemMetricaCard(
                  'R\$ / KM Global',
                  'R\$ ${fatKmGlobal.toStringAsFixed(2).replaceAll('.', ',')}',
                  Icons.directions_car,
                  Colors.blueAccent,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _buildItemMetricaCard(
                  'R\$ / KM Útil',
                  'R\$ ${fatKmUtil.toStringAsFixed(2).replaceAll('.', ',')}',
                  Icons.speed,
                  Colors.greenAccent,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _buildItemMetricaCard(
                  'Ticket Médio',
                  'R\$ ${ticketMedio.toStringAsFixed(2).replaceAll('.', ',')}',
                  Icons.receipt_long,
                  Colors.purpleAccent,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _buildItemMetricaCard(
                  'Total Corridas',
                  '$totalCorridas',
                  Icons.local_taxi,
                  Colors.orangeAccent,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildItemMetricaCard(String title, String val, IconData icon, Color accent) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: accent),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontSize: 10, color: FluentColors.textSecondary),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  val,
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
          ),
        ],
      ),
    );
  }

  Widget _buildFaturamentoPanel() {
    final fat = widget.jornada['faturamento'] as Map<String, dynamic>? ?? {};

    final double uberVal = double.tryParse('${fat['uber']}') ?? 0.0;
    final double noventaNoveVal = double.tryParse('${fat['noventa_nove']}') ?? 0.0;
    final double outrosVal = double.tryParse('${fat['outros']}') ?? double.tryParse('${fat['corridas_particulares']}') ?? 0.0;
    final double totalVal = double.tryParse('${fat['total_dia']}') ?? (uberVal + noventaNoveVal + outrosVal);

    final int uberCorr = int.tryParse('${fat['corridas_uber']}') ?? 0;
    final int noventaNoveCorr = int.tryParse('${fat['corridas_99']}') ?? 0;
    final int outrosCorr = int.tryParse('${fat['corridas_outros']}') ?? (widget.jornada['corridas_particulares'] as List?)?.length ?? 0;

    String fmt(double v) => 'R\$ ${v.toStringAsFixed(2).replaceAll('.', ',')}';

    return Card(
      color: const Color(0xFF1E293B),
      elevation: 6,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20), side: const BorderSide(color: Color(0xFF334155))),
      child: Padding(
        padding: const EdgeInsets.all(18.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Row(
                  children: [
                    Icon(Icons.account_balance_wallet, color: Color(0xFF34D399), size: 22),
                    SizedBox(width: 8),
                    Text(
                      'Faturamento da Jornada',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF10B981)),
                  ),
                  child: Text(
                    'Total: ${fmt(totalVal)}',
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12, color: Color(0xFF34D399)),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                // UBER CARD
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: Colors.white24),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('UBER', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: Colors.white70)),
                        const SizedBox(height: 4),
                        Text(fmt(uberVal), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white)),
                        const SizedBox(height: 2),
                        Text('$uberCorr corrida${uberCorr != 1 ? 's' : ''}', style: const TextStyle(fontSize: 10, color: Colors.grey)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                // 99 CARD
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF78350F).withOpacity(0.5),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: Colors.amber.withOpacity(0.5)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('99', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: Colors.amberAccent)),
                        const SizedBox(height: 4),
                        Text(fmt(noventaNoveVal), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.amberAccent)),
                        const SizedBox(height: 2),
                        Text('$noventaNoveCorr corrida${noventaNoveCorr != 1 ? 's' : ''}', style: const TextStyle(fontSize: 10, color: Colors.amber)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                // PARTICULAR CARD
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF064E3B).withOpacity(0.5),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: const Color(0xFF34D399).withOpacity(0.5)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('PARTICULAR', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: Color(0xFF34D399))),
                        const SizedBox(height: 4),
                        Text(fmt(outrosVal), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF34D399))),
                        const SizedBox(height: 2),
                        Text('$outrosCorr corrida${outrosCorr != 1 ? 's' : ''}', style: const TextStyle(fontSize: 10, color: Color(0xFFA7F3D0))),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCheckInInfo() {
    final fotos = widget.jornada['fotos'];
    final vistoria = widget.jornada['vistoria'];
    
    final kmInicialFotoUrl = fotos?['km_inicial_url'] as String?;
    final fotoAvariasUrl = vistoria?['foto_avarias_url'] as String?;
    
    final kmInicial = widget.jornada['km']?['inicial'] ?? 0;
    
    final checklistItems = <String>[];
    if (vistoria != null) {
      if (vistoria['pneus_ok'] == true) checklistItems.add('Pneus');
      if (vistoria['oleo_ok'] == true) checklistItems.add('Óleo');
      if (vistoria['agua_ok'] == true) checklistItems.add('Água');
      if (vistoria['farois_ok'] == true) checklistItems.add('Faróis');
      if (vistoria['limpeza_ok'] == true) checklistItems.add('Limpeza');
    }

    final hasKmFoto = kmInicialFotoUrl != null && kmInicialFotoUrl.isNotEmpty;
    final hasAvariaFoto = fotoAvariasUrl != null && fotoAvariasUrl.isNotEmpty;

    if (!hasKmFoto && !hasAvariaFoto && checklistItems.isEmpty) {
      return const SizedBox();
    }

    return Card(
      color: const Color(0xFF1E293B),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.assignment_turned_in_outlined, color: Colors.blueAccent, size: 22),
                SizedBox(width: 8),
                Text(
                  'Fotos e Vistoria de Início',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                ),
              ],
            ),
            const Divider(color: Colors.white10, height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text('Odômetro Inicial: $kmInicial km', style: const TextStyle(color: Colors.white70, fontSize: 13)),
                ),
                if (checklistItems.isNotEmpty)
                  Expanded(
                    child: Text(
                      'Itens OK: ${checklistItems.join(", ")}',
                      style: const TextStyle(color: Colors.grey, fontSize: 11),
                      textAlign: TextAlign.end,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                if (hasKmFoto)
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Foto do Odômetro', style: TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 6),
                        GestureDetector(
                          onTap: () => _mostrarImagemZoom(_getFullUrl(kmInicialFotoUrl), 'Odômetro Inicial'),
                          child: Container(
                            height: 100,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: Colors.white10),
                            ),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.network(
                                _getFullUrl(kmInicialFotoUrl),
                                fit: BoxFit.cover,
                                errorBuilder: (ctx, err, stack) => const Center(
                                  child: Icon(Icons.broken_image, color: Colors.redAccent),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                if (hasKmFoto && hasAvariaFoto)
                  const SizedBox(width: 16),
                if (hasAvariaFoto)
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Foto de Avarias', style: TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 6),
                        GestureDetector(
                          onTap: () => _mostrarImagemZoom(_getFullUrl(fotoAvariasUrl), 'Avarias do Veículo'),
                          child: Container(
                            height: 100,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: Colors.white10),
                            ),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.network(
                                _getFullUrl(fotoAvariasUrl),
                                fit: BoxFit.cover,
                                errorBuilder: (ctx, err, stack) => const Center(
                                  child: Icon(Icons.broken_image, color: Colors.redAccent),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricCard({required String title, required String value, required IconData icon, required Color color, String? subtitle}) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 12),
            Text(title, style: const TextStyle(fontSize: 13, color: Colors.grey)),
            const SizedBox(height: 4),
            Text(value, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
            if (subtitle != null) ...[
              const SizedBox(height: 6),
              Text(
                subtitle,
                style: const TextStyle(fontSize: 10, color: Colors.white54, height: 1.2),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton({required String title, required String subtitle, required IconData icon, required Color color, required VoidCallback onPressed}) {
    return Card(
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: color, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
                    const SizedBox(height: 2),
                    Text(subtitle, style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey),
            ],
          ),
        ),
      ),
    );
  }
}
