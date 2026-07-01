import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:app_motorista/core/api_service.dart';

class PausaScreen extends StatefulWidget {
  final Map<String, dynamic> jornada;
  final Function(Map<String, dynamic>) onResume;
  final VoidCallback onLogout;
  const PausaScreen({super.key, required this.jornada, required this.onResume, required this.onLogout});

  @override
  State<PausaScreen> createState() => _PausaScreenState();
}

class _PausaScreenState extends State<PausaScreen> {
  bool _loading = false;
  Duration _duration = Duration.zero;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  void _startTimer() {
    final pausas = widget.jornada['pausas'] as List;
    final ativa = pausas.firstWhere(
      (p) => p['fim'] == null,
      orElse: () => null,
    );

    if (ativa != null) {
      final hms = ativa['inicio'].split(':');
      final nowUtc = DateTime.now().toUtc();
      var inicioUtc = DateTime.utc(
        nowUtc.year,
        nowUtc.month,
        nowUtc.day,
        int.parse(hms[0]),
        int.parse(hms[1]),
        int.parse(hms[2].split('.')[0]),
      );
      if (inicioUtc.isAfter(nowUtc)) {
        inicioUtc = inicioUtc.subtract(const Duration(days: 1));
      }
      final inicioDt = inicioUtc.toLocal();

      _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
        setState(() {
          _duration = DateTime.now().difference(inicioDt);
        });
      });
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _retomarJornada() async {
    setState(() {
      _loading = true;
    });

    try {
      final pausas = widget.jornada['pausas'] as List;
      final ativa = pausas.firstWhere((p) => p['fim'] == null, orElse: () => null);

      if (ativa != null) {
        final jId = widget.jornada['_id'] ?? widget.jornada['id'];
        final res = await http.patch(
          Uri.parse('${ApiService.baseUrl}/jornadas/$jId/pausas/${ativa['id']}/fechar?localizacao_lat=-20.219&localizacao_lon=-40.264'),
          headers: ApiService.headers,
        );

        if (res.statusCode == 200) {
          final body = json.decode(res.body);
          widget.onResume(body);
        }
      }
    } catch (_) {} finally {
      setState(() {
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final h = _duration.inHours.toString().padLeft(2, '0');
    final m = (_duration.inMinutes % 60).toString().padLeft(2, '0');
    final s = (_duration.inSeconds % 60).toString().padLeft(2, '0');

    return Scaffold(
      appBar: AppBar(
        title: const Text('Pausa Ativa'),
        automaticallyImplyLeading: false,
        backgroundColor: const Color(0xFF1E293B),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: widget.onLogout,
            tooltip: 'Sair / Deslogar',
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Icon(Icons.pause_circle_filled, size: 100, color: Colors.amber),
              const SizedBox(height: 24),
              const Text(
                'Jornada em Pausa',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 8),
              Text(
                'Duração da pausa: $h:$m:$s',
                style: const TextStyle(fontSize: 22, color: Colors.amber, fontFamily: 'monospace'),
              ),
              const SizedBox(height: 48),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF6366F1)),
                  onPressed: _loading ? null : _retomarJornada,
                  child: _loading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('REINICIAR JORNADA', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
