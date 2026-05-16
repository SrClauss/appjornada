import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import '../../../core/errors/api_exception.dart';
import '../../../shared/models/jornada_model.dart';
import '../../../shared/widgets/app_button.dart';
import '../../../shared/widgets/loading_overlay.dart';
import '../services/jornada_service.dart';

class JornadaAtivaScreen extends ConsumerStatefulWidget {
  final String jornadaId;
  const JornadaAtivaScreen({super.key, required this.jornadaId});

  @override
  ConsumerState<JornadaAtivaScreen> createState() => _JornadaAtivaScreenState();
}

class _JornadaAtivaScreenState extends ConsumerState<JornadaAtivaScreen> {
  JornadaModel? _jornada;
  bool _isLoading = true;
  bool _isBusy = false;
  Timer? _timer;
  Duration _elapsed = Duration.zero;

  @override
  void initState() {
    super.initState();
    _loadJornada();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _loadJornada() async {
    try {
      final j = await JornadaService.getJornadaAberta();
      setState(() {
        _jornada = j;
        _isLoading = false;
      });
      if (j != null && j.isAberta) _startTimer(j);
    } catch (_) {
      setState(() => _isLoading = false);
    }
  }

  void _startTimer(JornadaModel j) {
    _timer?.cancel();
    if (j.horario?.inicio == null) return;
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final parts = j.horario!.inicio!.split(':');
    if (parts.length < 2) return;
    final startTime = today.add(Duration(
      hours: int.tryParse(parts[0]) ?? 0,
      minutes: int.tryParse(parts[1]) ?? 0,
      seconds: parts.length > 2 ? (int.tryParse(parts[2]) ?? 0) : 0,
    ));
    _elapsed = now.difference(startTime);
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      setState(() => _elapsed += const Duration(seconds: 1));
    });
  }

  String _fmt(Duration d) {
    final h = d.inHours.toString().padLeft(2, '0');
    final m = (d.inMinutes % 60).toString().padLeft(2, '0');
    final s = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$h:$m:$s';
  }

  Future<Position?> _getGps() async {
    try {
      bool ok = await Geolocator.isLocationServiceEnabled();
      if (!ok) return null;
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied ||
          perm == LocationPermission.deniedForever) return null;
      return await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 8),
        ),
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> _pausar() async {
    final tipo = await _showPausaTipoDialog();
    if (tipo == null || _jornada == null) return;

    setState(() => _isBusy = true);
    try {
      final position = await _getGps();
      final updated = await JornadaService.pausarJornada(
        jornadaId: _jornada!.id,
        tipo: tipo,
        lat: position?.latitude,
        lon: position?.longitude,
      );
      _timer?.cancel();
      setState(() {
        _jornada = updated;
        _isBusy = false;
      });
    } on ApiException catch (e) {
      setState(() => _isBusy = false);
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } catch (_) {
      setState(() => _isBusy = false);
    }
  }

  Future<String?> _showPausaTipoDialog() {
    return showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Tipo de pausa'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _TipoTile(
              icon: Icons.pause_circle_outline,
              label: 'Pausa livre',
              value: 'PAUSA_MOTORISTA',
            ),
            _TipoTile(
              icon: Icons.restaurant,
              label: 'Almoço',
              value: 'ALMOCO',
            ),
            _TipoTile(
              icon: Icons.local_gas_station,
              label: 'Abastecimento',
              value: 'ABASTECIMENTO',
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _retomar() async {
    if (_jornada == null) return;
    final pausaId = _jornada!.pausaAtiva?.id;
    if (pausaId == null) return;

    setState(() => _isBusy = true);
    try {
      final position = await _getGps();
      final updated = await JornadaService.retomarJornada(
        jornadaId: _jornada!.id,
        pausaId: pausaId,
        lat: position?.latitude,
        lon: position?.longitude,
      );
      setState(() {
        _jornada = updated;
        _isBusy = false;
      });
      if (updated.isAberta) _startTimer(updated);
    } on ApiException catch (e) {
      setState(() => _isBusy = false);
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } catch (_) {
      setState(() => _isBusy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Jornada Ativa')),
      body: LoadingOverlay(
        isLoading: _isBusy,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _jornada == null
                ? const Center(child: Text('Nenhuma jornada ativa.'))
                : ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      // Timer
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: Column(
                            children: [
                              Text(
                                _fmt(_elapsed),
                                style: Theme.of(context)
                                    .textTheme
                                    .displayMedium
                                    ?.copyWith(fontWeight: FontWeight.bold),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                _jornada!.isEmPausa ? 'EM PAUSA' : 'EM ANDAMENTO',
                                style: TextStyle(
                                  color: _jornada!.isEmPausa
                                      ? Colors.orange
                                      : Colors.green,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      // Info cards
                      _InfoCard(jornada: _jornada!),
                      const SizedBox(height: 16),
                      // Actions
                      if (_jornada!.isAberta) ...[
                        AppButton(
                          label: 'Pausar',
                          icon: Icons.pause_rounded,
                          color: Colors.orange,
                          onPressed: _pausar,
                        ),
                        const SizedBox(height: 8),
                        AppButton(
                          label: 'Registrar Abastecimento',
                          icon: Icons.local_gas_station_rounded,
                          color: Colors.teal,
                          onPressed: () => context.push(
                            '/jornada/abastecimento/${_jornada!.id}',
                            extra: {'kmAtual': _jornada!.km?.inicial},
                          ),
                        ),
                      ] else if (_jornada!.isEmPausa) ...[
                        AppButton(
                          label: 'Retomar',
                          icon: Icons.play_arrow_rounded,
                          color: Colors.green,
                          onPressed: _retomar,
                        ),
                      ],
                      const SizedBox(height: 8),
                      AppButton(
                        label: 'Encerrar Jornada',
                        icon: Icons.stop_rounded,
                        color: Colors.red,
                        onPressed: () =>
                            context.push('/jornada/fechar/${_jornada!.id}'),
                      ),
                    ],
                  ),
      ),
    );
  }
}

class _TipoTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _TipoTile(
      {required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon),
      title: Text(label),
      onTap: () => Navigator.pop(context, value),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final JornadaModel jornada;
  const _InfoCard({required this.jornada});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Row(
              icon: Icons.attach_money,
              label: 'Faturamento',
              value:
                  'R\$ ${(jornada.faturamento?.totalDia ?? 0).toStringAsFixed(2)}',
            ),
            const SizedBox(height: 8),
            _Row(
              icon: Icons.speed,
              label: 'Km rodados',
              value: '${(jornada.km?.rodados ?? 0).toStringAsFixed(1)} km',
            ),
          ],
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  const _Row({required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 18, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 8),
        Text('$label: ',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant)),
        Text(value,
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(fontWeight: FontWeight.bold)),
      ],
    );
  }
}
