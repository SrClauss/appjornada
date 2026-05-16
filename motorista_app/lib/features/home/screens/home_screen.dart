import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/api/api_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../core/auth/auth_provider.dart';
import '../../../core/errors/api_exception.dart';
import '../../../shared/models/jornada_model.dart';
import '../../../shared/widgets/app_button.dart';
import '../widgets/jornada_status_card.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  JornadaModel? _jornada;
  bool _isLoading = true;
  String? _error;
  Timer? _timer;
  Duration _elapsed = Duration.zero;

  @override
  void initState() {
    super.initState();
    _fetchJornadaAberta();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchJornadaAberta() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final response = await apiClient.get(Endpoints.jornadaAberta);
      final data = response.data;
      if (data == null || data == false) {
        setState(() {
          _jornada = null;
          _isLoading = false;
        });
        _timer?.cancel();
      } else {
        final jornada = JornadaModel.fromJson(data as Map<String, dynamic>);
        setState(() {
          _jornada = jornada;
          _isLoading = false;
        });
        if (jornada.isAberta) _startTimer(jornada);
      }
    } on ApiException catch (e) {
      if (e.statusCode == 404) {
        // No open journey
        setState(() {
          _jornada = null;
          _isLoading = false;
        });
      } else {
        setState(() {
          _error = e.message;
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Erro ao carregar jornada.';
        _isLoading = false;
      });
    }
  }

  void _startTimer(JornadaModel jornada) {
    _timer?.cancel();
    if (jornada.horario?.inicio == null) return;

    // Calculate elapsed from journey start time
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final parts = jornada.horario!.inicio!.split(':');
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

  String _formatElapsed(Duration d) {
    final h = d.inHours.toString().padLeft(2, '0');
    final m = (d.inMinutes % 60).toString().padLeft(2, '0');
    final s = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$h:$m:$s';
  }

  Future<void> _logout() async {
    await ref.read(authProvider.notifier).logout();
    if (mounted) context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).user;

    return Scaffold(
      appBar: AppBar(
        title: Text('Olá, ${user?.nome.split(' ').first ?? 'Motorista'}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.history_rounded),
            tooltip: 'Histórico',
            onPressed: () => context.push('/historico'),
          ),
          IconButton(
            icon: const Icon(Icons.person_rounded),
            tooltip: 'Perfil',
            onPressed: () => context.push('/perfil'),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sair',
            onPressed: _logout,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _fetchJornadaAberta,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_error!,
                            style: TextStyle(
                                color: Theme.of(context).colorScheme.error)),
                        const SizedBox(height: 12),
                        TextButton(
                          onPressed: _fetchJornadaAberta,
                          child: const Text('Tentar novamente'),
                        ),
                      ],
                    ),
                  )
                : ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      JornadaStatusCard(jornada: _jornada),
                      const SizedBox(height: 16),
                      if (_jornada == null) ...[
                        AppButton(
                          label: 'Abrir Jornada',
                          icon: Icons.play_arrow_rounded,
                          onPressed: () => context.push('/jornada/abrir'),
                        ),
                      ] else if (_jornada!.isAberta) ...[
                        // Timer
                        Center(
                          child: Text(
                            _formatElapsed(_elapsed),
                            style: Theme.of(context)
                                .textTheme
                                .displaySmall
                                ?.copyWith(
                                  fontWeight: FontWeight.bold,
                                  fontFeatures: const [
                                    // monospace digits
                                  ],
                                ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        AppButton(
                          label: 'Pausar',
                          icon: Icons.pause_rounded,
                          color: Colors.orange,
                          onPressed: () =>
                              context.push('/jornada/pausar/${_jornada!.id}'),
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
                        const SizedBox(height: 8),
                        AppButton(
                          label: 'Encerrar Jornada',
                          icon: Icons.stop_rounded,
                          color: Colors.red,
                          onPressed: () =>
                              context.push('/jornada/fechar/${_jornada!.id}'),
                        ),
                      ] else if (_jornada!.isEmPausa) ...[
                        AppButton(
                          label: 'Retomar Jornada',
                          icon: Icons.play_arrow_rounded,
                          color: Colors.green,
                          onPressed: () {
                            final pausaId = _jornada!.pausaAtiva?.id;
                            if (pausaId != null) {
                              context.push(
                                '/jornada/retomar/${_jornada!.id}/$pausaId',
                              );
                            }
                          },
                        ),
                        const SizedBox(height: 8),
                        AppButton(
                          label: 'Encerrar Jornada',
                          icon: Icons.stop_rounded,
                          color: Colors.red,
                          onPressed: () =>
                              context.push('/jornada/fechar/${_jornada!.id}'),
                        ),
                      ],
                    ],
                  ),
      ),
    );
  }
}
