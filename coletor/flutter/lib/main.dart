import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

const MethodChannel _channel = MethodChannel('appjornada/coletor_monitor');

const String _serverBaseUrl = 'http://2.24.121.189/api';
const String _uploadRoute = '/coleta/upload';
const String _apiKey = 'coleta-dev-key';
const List<String> _targetPackages = <String>[
  'com.app99.driver',
  'com.ubercab.driver',
  'com.github.android',
  'com.github.android.beta',
];

void main() {
  runApp(const ColetorApp());
}

class ColetorApp extends StatelessWidget {
  const ColetorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AppJornada Coletor',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
      ),
      home: const ColetorHomePage(),
    );
  }
}

class _ColetaEvento {
  _ColetaEvento({
    required this.packageName,
    required this.activityClass,
    required this.timestamp,
  });

  final String packageName;
  final String activityClass;
  final DateTime timestamp;

  factory _ColetaEvento.fromMap(Map<String, dynamic> data) {
    final timestampRaw = data['timestamp'];
    final timestampMs = timestampRaw is num ? timestampRaw.toInt() : 0;

    return _ColetaEvento(
      packageName: data['packageName']?.toString() ?? 'desconhecido',
      activityClass: data['activityClass']?.toString().trim().isNotEmpty == true
          ? data['activityClass'].toString()
          : '(sem activity)',
      timestamp: DateTime.fromMillisecondsSinceEpoch(timestampMs),
    );
  }
}

class ColetorHomePage extends StatefulWidget {
  const ColetorHomePage({super.key});

  @override
  State<ColetorHomePage> createState() => _ColetorHomePageState();
}

class _ColetorHomePageState extends State<ColetorHomePage> {
  bool _enabled = false;
  int _eventCount = 0;
  bool _sending = false;
  String _status = 'Carregando status...';
  List<_ColetaEvento> _events = const <_ColetaEvento>[];
  final List<String> _uploadLogs = <String>[];

  @override
  void initState() {
    super.initState();
    _refreshAll();
  }

  Future<void> _refreshAll() async {
    await Future.wait(<Future<void>>[
      _refreshStatus(),
      _refreshEvents(),
    ]);
  }

  Future<void> _refreshStatus() async {
    try {
      final status = await _channel.invokeMapMethod<String, dynamic>('status');
      setState(() {
        _enabled = status?['accessibilityEnabled'] == true;
        _eventCount = (status?['eventCount'] as int?) ?? 0;
        _status = _enabled
            ? 'Monitoramento ativo em background.'
            : 'Ative o serviço de acessibilidade para iniciar a coleta.';
      });
    } catch (e) {
      setState(() => _status = 'Falha ao ler status: $e');
    }
  }

  Future<void> _refreshEvents() async {
    try {
      final payload = await _channel.invokeMethod<List<dynamic>>('eventsForUpload');
      final rows = payload
              ?.whereType<Map>()
              .map((e) => e.map((key, value) => MapEntry(key.toString(), value)))
              .toList() ??
          <Map<String, dynamic>>[];

      final loaded = rows
          .map(_ColetaEvento.fromMap)
          .toList()
        ..sort((a, b) => b.timestamp.compareTo(a.timestamp));

      setState(() {
        _events = loaded;
        _eventCount = loaded.length;
      });
    } catch (e) {
      _addLog('Falha ao carregar eventos locais: $e');
    }
  }

  Future<void> _openAccessibilitySettings() async {
    try {
      await _channel.invokeMethod('openAccessibilitySettings');
    } catch (e) {
      setState(() => _status = 'Não foi possível abrir configurações: $e');
    }
  }

  Future<void> _clearEvents() async {
    await _channel.invokeMethod('clearEvents');
    _addLog('Dados locais removidos pelo usuário.');
    await _refreshAll();
  }

  void _addLog(String message) {
    final now = DateTime.now();
    final timestamp =
        '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}:${now.second.toString().padLeft(2, '0')}';
    setState(() {
      _uploadLogs.insert(0, '[$timestamp] $message');
      if (_uploadLogs.length > 200) {
        _uploadLogs.removeRange(200, _uploadLogs.length);
      }
    });
  }

  Future<void> _sendNow() async {
    setState(() {
      _sending = true;
      _status = 'Preparando envio...';
    });

    _addLog('Iniciando preparo do payload.');

    try {
      final rows = _events
          .map(
            (event) => <String, dynamic>{
              'timestamp': event.timestamp.millisecondsSinceEpoch,
              'packageName': event.packageName,
              'activityClass': event.activityClass,
            },
          )
          .toList();

      if (rows.isEmpty) {
        _addLog('Sem dados locais para envio.');
        setState(() {
          _status = 'Sem dados para enviar.';
          _sending = false;
        });
        return;
      }

      final now = DateTime.now();
      final date =
          '${now.year.toString().padLeft(4, '0')}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      final jsonl = rows.map(jsonEncode).join('\n');

      final tempDir = Directory.systemTemp;
      final file = File('${tempDir.path}/coleta_apps_$date.jsonl');
      await file.writeAsString('$jsonl\n', flush: true);

      _addLog('Arquivo local gerado: ${file.path} (${rows.length} eventos).');

      final dispositivo = await _channel.invokeMethod<String>('deviceLabel') ?? 'android';
      final data = FormData.fromMap({
        'dispositivo': dispositivo,
        'arquivo': await MultipartFile.fromFile(
          file.path,
          filename: 'coletor_apps_$date.jsonl',
        ),
      });

      final dio = Dio(
        BaseOptions(
          baseUrl: _serverBaseUrl,
          connectTimeout: const Duration(seconds: 20),
          receiveTimeout: const Duration(seconds: 60),
          headers: {'X-API-Key': _apiKey},
        ),
      );

      _addLog('Enviando dados para $_serverBaseUrl$_uploadRoute.');
      final response = await dio.post(_uploadRoute, data: data);
      final responseBody = response.data;

      _addLog('Resposta do servidor: HTTP ${response.statusCode} - $responseBody');

      if (response.statusCode == 200) {
        await _channel.invokeMethod('markEventsAsSent');
        final inserted = responseBody is Map ? responseBody['telas_inseridas'] : null;
        setState(() {
          _status = 'Envio concluído com sucesso. Telas inseridas: $inserted';
        });
      } else {
        setState(() {
          _status = 'Falha no envio. HTTP ${response.statusCode}';
        });
      }
    } on DioException catch (e) {
      _addLog('Erro de rede: ${e.message}');
      if (e.response != null) {
        _addLog('Detalhe servidor: HTTP ${e.response?.statusCode} - ${e.response?.data}');
      }
      setState(() => _status = 'Erro no envio: ${e.message}');
    } catch (e) {
      _addLog('Erro inesperado no envio: $e');
      setState(() => _status = 'Erro no envio: $e');
    } finally {
      setState(() => _sending = false);
      await _refreshAll();
    }
  }

  Map<String, int> _countByPackage() {
    final counter = <String, int>{for (final pkg in _targetPackages) pkg: 0};
    for (final event in _events) {
      counter.update(
        event.packageName,
        (value) => value + 1,
        ifAbsent: () => 1,
      );
    }
    return counter;
  }

  String _formatDate(DateTime date) {
    final yyyy = date.year.toString().padLeft(4, '0');
    final mm = date.month.toString().padLeft(2, '0');
    final dd = date.day.toString().padLeft(2, '0');
    final hh = date.hour.toString().padLeft(2, '0');
    final mi = date.minute.toString().padLeft(2, '0');
    final ss = date.second.toString().padLeft(2, '0');
    return '$yyyy-$mm-$dd $hh:$mi:$ss';
  }

  Widget _buildMonitorTab() {
    final packageCounter = _countByPackage();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(_status),
        const SizedBox(height: 8),
        Text('Eventos coletados: $_eventCount'),
        const SizedBox(height: 12),
        const Text('Pacotes monitorados:'),
        const SizedBox(height: 8),
        ..._targetPackages.map(
          (pkg) => Text('- $pkg (${packageCounter[pkg] ?? 0} eventos)'),
        ),
        const SizedBox(height: 20),
        ElevatedButton(
          onPressed: _openAccessibilitySettings,
          child: const Text('Ativar monitoramento em background'),
        ),
        const SizedBox(height: 8),
        OutlinedButton(
          onPressed: _refreshAll,
          child: const Text('Atualizar status e dados'),
        ),
      ],
    );
  }

  Widget _buildDataTab() {
    final preview = _events.take(100).toList();

    if (_events.isEmpty) {
      return const Center(
        child: Text('Nenhum dado coletado ainda.'),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: preview.length,
      separatorBuilder: (_, __) => const Divider(height: 16),
      itemBuilder: (context, index) {
        final event = preview[index];
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(event.packageName, style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 4),
            Text(event.activityClass),
            const SizedBox(height: 4),
            Text(_formatDate(event.timestamp), style: const TextStyle(fontSize: 12)),
          ],
        );
      },
    );
  }

  Widget _buildUploadTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ElevatedButton(
            onPressed: _sending ? null : _sendNow,
            child: _sending
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Enviar dados do dia'),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            onPressed: _clearEvents,
            child: const Text('Limpar dados locais'),
          ),
          const SizedBox(height: 16),
          const Text('Logs de envio', style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Expanded(
            child: _uploadLogs.isEmpty
                ? const Text('Nenhum log ainda.')
                : ListView.builder(
                    itemCount: _uploadLogs.length,
                    itemBuilder: (context, index) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(_uploadLogs[index]),
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Coletor AppJornada'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Monitor'),
              Tab(text: 'Dados'),
              Tab(text: 'Envio'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _buildMonitorTab(),
            _buildDataTab(),
            _buildUploadTab(),
          ],
        ),
      ),
    );
  }
}
