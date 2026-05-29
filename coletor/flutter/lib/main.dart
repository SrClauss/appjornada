import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

const MethodChannel _channel = MethodChannel('appjornada/coletor_monitor');

const String _serverBaseUrl = 'http://2.24.121.189/api';
const String _uploadRoute = '/coleta/upload';
const String _apiKey = 'coleta-dev-key';

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

class ColetorHomePage extends StatefulWidget {
  const ColetorHomePage({super.key});

  @override
  State<ColetorHomePage> createState() => _ColetorHomePageState();
}

class _ColetorHomePageState extends State<ColetorHomePage> {
  bool _enabled = false;
  int _eventCount = 0;
  String _status = 'Carregando status...';
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _refreshStatus();
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

  Future<void> _openAccessibilitySettings() async {
    try {
      await _channel.invokeMethod('openAccessibilitySettings');
    } catch (e) {
      setState(() => _status = 'Não foi possível abrir configurações: $e');
    }
  }

  Future<void> _clearEvents() async {
    await _channel.invokeMethod('clearEvents');
    await _refreshStatus();
  }

  Future<void> _sendNow() async {
    setState(() {
      _sending = true;
      _status = 'Preparando envio...';
    });

    try {
      final payload = await _channel.invokeMethod<List<dynamic>>('eventsForUpload');
      final rows = payload
              ?.whereType<Map>()
              .map((e) => e.map((key, value) => MapEntry(key.toString(), value)))
              .toList() ??
          <Map<String, dynamic>>[];

      if (rows.isEmpty) {
        setState(() {
          _status = 'Sem dados para enviar.';
          _sending = false;
        });
        return;
      }

      final now = DateTime.now();
      final date = '${now.year.toString().padLeft(4, '0')}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      final jsonl = rows.map(jsonEncode).join('\n');

      final tempDir = Directory.systemTemp;
      final file = File('${tempDir.path}/coleta_apps_$date.jsonl');
      await file.writeAsString('$jsonl\n', flush: true);

      final data = FormData.fromMap({
        'dispositivo': await _channel.invokeMethod<String>('deviceLabel') ?? 'android',
        'arquivo': await MultipartFile.fromFile(
          file.path,
          filename: 'coletor_apps_$date.jsonl',
        ),
      });

      final dio = Dio(BaseOptions(
        baseUrl: _serverBaseUrl,
        connectTimeout: const Duration(seconds: 20),
        receiveTimeout: const Duration(seconds: 60),
        headers: {'X-API-Key': _apiKey},
      ));

      final response = await dio.post(_uploadRoute, data: data);
      if (response.statusCode == 200) {
        await _channel.invokeMethod('markEventsAsSent');
        final inserted = response.data is Map ? response.data['telas_inseridas'] : null;
        setState(() => _status = 'Envio concluído com sucesso. Telas inseridas: $inserted');
      } else {
        setState(() => _status = 'Falha no envio. HTTP ${response.statusCode}');
      }
    } catch (e) {
      setState(() => _status = 'Erro no envio: $e');
    } finally {
      setState(() => _sending = false);
      await _refreshStatus();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Coletor AppJornada'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Pacotes monitorados: com.app99.driver, com.ubercab.driver, com.github.android',
            ),
            const SizedBox(height: 12),
            Text(_status),
            const SizedBox(height: 8),
            Text('Eventos coletados: $_eventCount'),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _openAccessibilitySettings,
              child: const Text('Ativar monitoramento em background'),
            ),
            const SizedBox(height: 8),
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
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: _refreshStatus,
              child: const Text('Atualizar status'),
            ),
          ],
        ),
      ),
    );
  }
}
