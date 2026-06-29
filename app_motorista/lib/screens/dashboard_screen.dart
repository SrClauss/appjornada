import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:app_motorista/core/api_service.dart';
import 'package:app_motorista/widgets/abastecimento_modal.dart';
import 'package:app_motorista/widgets/manutencao_dialog.dart';
import 'package:app_motorista/widgets/encerrar_jornada_dialog.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';

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

  @override
  void initState() {
    super.initState();
    _checkWeekendOrHoliday();
    _startTimer();
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

  String _formatTimer() {
    if (_isWeekendOrHoliday) {
      // Começa em 00:00:00 e conta positivo
      final h = _elapsedJornada.inHours.toString().padLeft(2, '0');
      final m = (_elapsedJornada.inMinutes % 60).toString().padLeft(2, '0');
      final s = (_elapsedJornada.inSeconds % 60).toString().padLeft(2, '0');
      return '$h:$m:$s';
    } else {
      // Inicia negativo (-08:48:00) e desconta
      if (_elapsedJornada < _metaCLT) {
        final restante = _metaCLT - _elapsedJornada;
        final h = restante.inHours.toString().padLeft(2, '0');
        final m = (restante.inMinutes % 60).toString().padLeft(2, '0');
        final s = (restante.inSeconds % 60).toString().padLeft(2, '0');
        return '-$h:$m:$s';
      } else {
        // Horas extras (positivo)
        final extras = _elapsedJornada - _metaCLT;
        final h = extras.inHours.toString().padLeft(2, '0');
        final m = (extras.inMinutes % 60).toString().padLeft(2, '0');
        final s = (extras.inSeconds % 60).toString().padLeft(2, '0');
        return '+$h:$m:$s';
      }
    }
  }

  Color _getTimerColor() {
    if (_isWeekendOrHoliday) return Colors.greenAccent;
    if (_elapsedJornada < _metaCLT) return Colors.redAccent;
    return Colors.greenAccent;
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

  Future<void> _enviarPrint() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery);
    if (picked != null) {
      widget.onAction('processar_print', {'path': picked.path});
    }
  }

  Future<void> _encerrarJornada() async {
    widget.onAction('close_wizard', null);
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
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // CARD CRONÔMETRO
            Card(
              elevation: 4,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Container(
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
                    const Text(
                      'STATUS DA JORNADA: ATIVA',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, letterSpacing: 1.5, color: Colors.blueAccent),
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
                      _isWeekendOrHoliday
                          ? 'Final de semana / Feriado (100% Extra)'
                          : (_elapsedJornada < _metaCLT ? 'Restante para fechar 08:48h' : 'Horas Extras Acumuladas'),
                      style: const TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              ),
            ),
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
                    title: 'Bônus Acumulado',
                    value: 'R\$ 320,00',
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
            // BOTÕES DE AÇÃO
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
              onPressed: _iniciarPausa,
            ),
            const SizedBox(height: 16),
            _buildActionButton(
              title: 'ENVIAR PRINT DE FATURAMENTO',
              subtitle: 'Envie capturas de tela da Uber/99 para processar',
              icon: Icons.image,
              color: Colors.teal,
              onPressed: _enviarPrint,
            ),
            const SizedBox(height: 16),
            _buildActionButton(
              title: 'CORRIDA PARTICULAR',
              subtitle: 'Gerencie e calcule viagens particulares em tempo real',
              icon: Icons.directions_car,
              color: Colors.green,
              onPressed: () {
                widget.onAction('corrida_particular', null);
              },
            ),
            const SizedBox(height: 16),
            _buildActionButton(
              title: 'MANUTENÇÃO',
              subtitle: 'Entrada em oficina ou preventiva',
              icon: Icons.build,
              color: Colors.redAccent,
              onPressed: _abrirManutencao,
            ),
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
    );
  }

  Widget _buildMetricCard({required String title, required String value, required IconData icon, required Color color}) {
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
