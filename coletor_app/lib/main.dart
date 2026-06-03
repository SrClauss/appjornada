import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

void main() {
  runApp(const ColetorApp());
}

class ColetorApp extends StatelessWidget {
  const ColetorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RPA Coletor',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0F172A), // Slate 900
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF10B981), // Emerald 500
          secondary: Color(0xFF06B6D4), // Cyan 500
          surface: Color(0xFF1E293B), // Slate 800
          background: Color(0xFF0F172A), // Slate 900
        ),
        cardTheme: const CardThemeData(
          color: Color(0xFF1E293B), // Slate 800
          elevation: 2,
          margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        ),
      ),
      home: const DashboardPage(),
    );
  }
}

class LogItem {
  final DateTime timestamp;
  final String packageName;
  final String className;
  final String eventType;
  final Map<String, dynamic> tree;
  final List<String> flatTexts;
  bool isSynced;

  LogItem({
    required this.timestamp,
    required this.packageName,
    required this.className,
    required this.eventType,
    required this.tree,
    required this.flatTexts,
    this.isSynced = false,
  });
}

class UploadHistoryItem {
  final DateTime timestamp;
  final String filename;
  final int recordCount;
  final String status; // 'SUCESSO' ou 'ERRO'
  final String responseMessage;

  UploadHistoryItem({
    required this.timestamp,
    required this.filename,
    required this.recordCount,
    required this.status,
    required this.responseMessage,
  });
}

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  static const EventChannel _eventChannel = EventChannel('com.example.myapp/accessibility');
  static const MethodChannel _methodChannel = MethodChannel('com.example.myapp/utils');

  StreamSubscription? _subscription;
  final List<LogItem> _logs = [];
  final List<UploadHistoryItem> _uploadHistory = [];
  String _searchQuery = '';
  bool _isPaused = false;

  // Configurações de Persistência Local
  int _totalPendingCount = 0;

  // Configurações do Servidor
  final TextEditingController _urlController = TextEditingController(text: 'http://2.24.121.189:3000/api');
  final TextEditingController _keyController = TextEditingController(text: 'coleta-dev-key');
  final TextEditingController _deviceController = TextEditingController(text: 'Celular Motorista');
  bool _isSyncing = false;
  bool _showSettings = false;

  @override
  void initState() {
    super.initState();
    _loadLogsFromDisk();
    _startListening();
  }

  @override
  void dispose() {
    _stopListening();
    _urlController.dispose();
    _keyController.dispose();
    _deviceController.dispose();
    super.dispose();
  }

  // Pega o caminho do arquivo persistente local
  Future<File> get _localFile async {
    final directory = await getApplicationDocumentsDirectory();
    return File('${directory.path}/logs_acumulados.jsonl');
  }

  // Carrega os logs salvos em disco no carregamento da tela
  Future<void> _loadLogsFromDisk() async {
    try {
      final file = await _localFile;
      if (!await file.exists()) {
        setState(() {
          _totalPendingCount = 0;
        });
        return;
      }
      final lines = await file.readAsLines();
      final List<LogItem> loaded = [];

      for (var line in lines) {
        if (line.trim().isEmpty) continue;
        try {
          final data = jsonDecode(line);
          final List<String> flatTexts = _extractFlatTexts(data['tree'] ?? {});
          loaded.insert(
            0,
            LogItem(
              timestamp: DateTime.parse(data['timestamp']),
              packageName: data['packageName'] ?? '',
              className: data['activityClass'] ?? '',
              eventType: data['eventType'] ?? '',
              tree: data['tree'] ?? {},
              flatTexts: flatTexts,
              isSynced: false,
            ),
          );
        } catch (_) {}
      }

      setState(() {
        _logs.clear();
        // Mantém apenas os últimos 50 na RAM para não pesar a UI visual
        _logs.addAll(loaded.take(50));
        _totalPendingCount = loaded.length;
      });
    } catch (e) {
      debugPrint("Erro ao ler logs do disco: $e");
    }
  }

  // Grava o novo log no arquivo de lote do disco
  Future<void> _saveLogToDisk(LogItem log) async {
    try {
      final file = await _localFile;
      final String line = jsonEncode({
        "timestamp": log.timestamp.toIso8601String(),
        "packageName": log.packageName,
        "activityClass": log.className,
        "eventType": log.eventType,
        "tree": log.tree,
      }) + '\n';
      await file.writeAsString(line, mode: FileMode.append);
    } catch (e) {
      debugPrint("Erro ao salvar log no disco: $e");
    }
  }

  List<String> _extractFlatTexts(Map<String, dynamic> node) {
    final List<String> texts = [];
    final String text = node['text']?.toString() ?? '';
    if (text.isNotEmpty) {
      texts.add(text);
    }
    final String desc = node['contentDescription']?.toString() ?? '';
    if (desc.isNotEmpty) {
      texts.add(desc);
    }
    final children = node['children'];
    if (children is List) {
      for (var child in children) {
        if (child is Map) {
          texts.addAll(_extractFlatTexts(Map<String, dynamic>.from(child)));
        }
      }
    }
    return texts;
  }

  void _startListening() {
    _subscription = _eventChannel.receiveBroadcastStream().listen((dynamic event) {
      if (_isPaused) return;

      if (event is Map) {
        final Map<String, dynamic> data = Map<String, dynamic>.from(event);
        final Map<String, dynamic> tree = Map<String, dynamic>.from(data['tree'] ?? {});

        if (tree.isEmpty) return;

        final flatTexts = _extractFlatTexts(tree);
        final newLog = LogItem(
          timestamp: DateTime.now(),
          packageName: data['packageName'] ?? '',
          className: data['className'] ?? '',
          eventType: data['eventType'] ?? '',
          tree: tree,
          flatTexts: flatTexts,
          isSynced: false,
        );

        // Salva silenciosamente em disco no arquivo do lote acumulado
        _saveLogToDisk(newLog);

        setState(() {
          // Insere na visualização da tela
          _logs.insert(0, newLog);
          if (_logs.length > 50) {
            _logs.removeLast(); // Mantém UI leve
          }
          _totalPendingCount++;
        });
      }
    }, onError: (dynamic error) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro no Stream de Acessibilidade: $error')),
      );
    });
  }

  void _stopListening() {
    _subscription?.cancel();
    _subscription = null;
  }

  Future<void> _openAccessibilitySettings() async {
    try {
      await _methodChannel.invokeMethod('openAccessibilitySettings');
    } on PlatformException catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao abrir configurações: ${e.message}')),
      );
    }
  }

  // Envia todo o arquivo .jsonl acumulado localmente para o servidor
  Future<void> _syncDailyLogs() async {
    final file = await _localFile;
    if (!await file.exists() || _totalPendingCount == 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Nenhum log acumulado para enviar!')),
      );
      return;
    }

    setState(() {
      _isSyncing = true;
    });

    final int recordCount = _totalPendingCount;
    final String dateStr = DateTime.now().toIso8601String().replaceAll(':', '-');
    final String filename = "coleta_diaria_$dateStr.jsonl";

    try {
      final String baseUrl = _urlController.text.trim();
      final Uri uri = Uri.parse("$baseUrl/coleta/upload");

      final request = http.MultipartRequest('POST', uri);
      request.headers['x-api-key'] = _keyController.text.trim();

      // Envia o arquivo persistente do disco diretamente
      final filePart = await http.MultipartFile.fromPath(
        'arquivo',
        file.path,
        filename: filename,
      );
      request.files.add(filePart);

      final deviceName = _deviceController.text.trim();
      if (deviceName.isNotEmpty) {
        request.fields['dispositivo'] = deviceName;
      }

      final response = await request.send();
      final body = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        // Limpa o arquivo de lote acumulado no disco, pois o upload deu OK!
        await file.delete();

        setState(() {
          for (var log in _logs) {
            log.isSynced = true;
          }
          _totalPendingCount = 0;
          _uploadHistory.insert(
            0,
            UploadHistoryItem(
              timestamp: DateTime.now(),
              filename: filename,
              recordCount: recordCount,
              status: 'SUCESSO',
              responseMessage: body,
            ),
          );
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$recordCount logs do dia enviados com sucesso!'),
            backgroundColor: Colors.green,
          ),
        );
      } else {
        setState(() {
          _uploadHistory.insert(
            0,
            UploadHistoryItem(
              timestamp: DateTime.now(),
              filename: filename,
              recordCount: recordCount,
              status: 'ERRO',
              responseMessage: 'Status ${response.statusCode}: $body',
            ),
          );
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Falha no upload (Status ${response.statusCode}). Verifique o histórico de envios.'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      setState(() {
        _uploadHistory.insert(
          0,
          UploadHistoryItem(
            timestamp: DateTime.now(),
            filename: filename,
            recordCount: recordCount,
            status: 'ERRO',
            responseMessage: e.toString(),
          ),
        );
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Erro excepcional de rede: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      setState(() {
        _isSyncing = false;
      });
    }
  }

  // Deleta o arquivo acumulado e limpa histórico local
  Future<void> _clearLocalLogs() async {
    final file = await _localFile;
    if (await file.exists()) {
      await file.delete();
    }
    setState(() {
      _logs.clear();
      _totalPendingCount = 0;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Cache local de logs do dia limpo.')),
    );
  }

  List<LogItem> get _filteredLogs {
    if (_searchQuery.isEmpty) return _logs;

    final query = _searchQuery.toLowerCase();
    return _logs.where((log) {
      final matchPackage = log.packageName.toLowerCase().contains(query);
      final matchClass = log.className.toLowerCase().contains(query);
      final matchTexts = log.flatTexts.any((text) => text.toLowerCase().contains(query));
      return matchPackage || matchClass || matchTexts;
    }).toList();
  }

  void _showTreeDetails(LogItem log) {
    final String formattedJson = const JsonEncoder.withIndent('  ').convert(log.tree);

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F172A),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return DraggableScrollableSheet(
          initialChildSize: 0.8,
          maxChildSize: 0.95,
          minChildSize: 0.5,
          expand: false,
          builder: (context, scrollController) {
            return Column(
              children: [
                Container(
                  margin: const EdgeInsets.only(top: 12, bottom: 8),
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white24,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              log.packageName,
                              style: const TextStyle(
                                color: Color(0xFF06B6D4),
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Árvore de Componentes (Bounds & Propriedades)',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.5),
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.copy_outlined, color: Color(0xFF10B981)),
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: formattedJson));
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Estrutura copiada para a área de transferência!')),
                          );
                        },
                      ),
                    ],
                  ),
                ),
                const Divider(color: Colors.white10),
                Expanded(
                  child: Container(
                    margin: const EdgeInsets.all(16),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: const Color(0xFF050B14),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.white10),
                    ),
                    child: SingleChildScrollView(
                      controller: scrollController,
                      child: SelectableText(
                        formattedJson,
                        style: const TextStyle(
                          fontFamily: 'monospace',
                          fontSize: 12,
                          color: Color(0xFF10B981),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredLogs;

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Row(
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: _isPaused ? Colors.amber : Colors.green,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: _isPaused ? Colors.amber.withOpacity(0.5) : Colors.green.withOpacity(0.5),
                      blurRadius: 6,
                      spreadRadius: 2,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              const Text(
                'RPA Coletor Logs',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 20),
              ),
            ],
          ),
          backgroundColor: const Color(0xFF1E293B),
          elevation: 4,
          actions: [
            IconButton(
              tooltip: 'Configurações de Conexão',
              icon: Icon(Icons.cloud_upload_outlined, color: _showSettings ? const Color(0xFF10B981) : const Color(0xFF06B6D4)),
              onPressed: () {
                setState(() {
                  _showSettings = !_showSettings;
                });
              },
            ),
            IconButton(
              tooltip: 'Configurações de Acessibilidade',
              icon: const Icon(Icons.settings, color: Colors.white70),
              onPressed: _openAccessibilitySettings,
            ),
            IconButton(
              tooltip: 'Limpar Logs Acumulados',
              icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
              onPressed: () {
                // Alerta para confirmar limpeza
                showDialog(
                  context: context,
                  builder: (context) => AlertDialog(
                    title: const Text('Limpar Cache de Logs?'),
                    content: const Text('Isso apagará todos os logs acumulados hoje do armazenamento do telefone.'),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
                      TextButton(
                        onPressed: () {
                          Navigator.pop(context);
                          _clearLocalLogs();
                        },
                        child: const Text('Confirmar', style: TextStyle(color: Colors.redAccent)),
                      ),
                    ],
                  ),
                );
              },
            ),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.radar), text: 'Layouts Recentes'),
              Tab(icon: Icon(Icons.cloud_sync), text: 'Logs de Envios'),
            ],
            indicatorColor: Color(0xFF10B981),
            labelColor: Color(0xFF10B981),
            unselectedLabelColor: Colors.white60,
          ),
        ),
        body: Column(
          children: [
            // Painel de Configurações do Servidor (Expansível)
            AnimatedCrossFade(
              firstChild: const SizedBox.shrink(),
              secondChild: Container(
                padding: const EdgeInsets.all(16),
                decoration: const BoxDecoration(
                  color: Color(0xFF1E293B),
                  border: Border(bottom: BorderSide(color: Colors.white10)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'CONEXÃO COM O SERVIDOR',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF06B6D4)),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _urlController,
                      decoration: const InputDecoration(
                        labelText: 'URL base da API (Nginx /api)',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _keyController,
                            decoration: const InputDecoration(
                              labelText: 'Chave API (x-api-key)',
                              border: OutlineInputBorder(),
                              contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: TextField(
                            controller: _deviceController,
                            decoration: const InputDecoration(
                              labelText: 'Identificador do Aparelho',
                              border: OutlineInputBorder(),
                              contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              crossFadeState: _showSettings ? CrossFadeState.showSecond : CrossFadeState.showFirst,
              duration: const Duration(milliseconds: 250),
            ),

            // Tab Views
            Expanded(
              child: TabBarView(
                children: [
                  // Tab 1: Radar de Layouts do Dia
                  Column(
                    children: [
                      // Painel Superior de Status e Ação de Sincronização Única
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        color: const Color(0xFF1E293B),
                        child: Column(
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Logs Acumulados: $_totalPendingCount',
                                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
                                    ),
                                    const SizedBox(height: 2),
                                    const Text(
                                      'Salvos localmente no disco',
                                      style: TextStyle(fontSize: 11, color: Colors.white38),
                                    ),
                                  ],
                                ),
                                Row(
                                  children: [
                                    if (_isSyncing)
                                      const Padding(
                                        padding: EdgeInsets.symmetric(horizontal: 12),
                                        child: SizedBox(
                                          width: 20,
                                          height: 20,
                                          child: CircularProgressIndicator(strokeWidth: 2),
                                        ),
                                      )
                                    else
                                      ElevatedButton.icon(
                                        onPressed: _syncDailyLogs,
                                        icon: const Icon(Icons.cloud_upload_sharp, size: 16),
                                        label: const Text('Enviar para o Servidor'),
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: const Color(0xFF10B981), // Emerald 500
                                          foregroundColor: Colors.white,
                                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                        ),
                                      ),
                                    const SizedBox(width: 8),
                                    IconButton(
                                      tooltip: _isPaused ? 'Retomar captura' : 'Pausar captura',
                                      icon: Icon(_isPaused ? Icons.play_arrow : Icons.pause, color: _isPaused ? Colors.green : Colors.amber),
                                      onPressed: () {
                                        setState(() {
                                          _isPaused = !_isPaused;
                                        });
                                      },
                                    ),
                                  ],
                                ),
                              ],
                            ),
                            const SizedBox(height: 10),
                            TextField(
                              onChanged: (val) {
                                setState(() {
                                  _searchQuery = val;
                                });
                              },
                              decoration: InputDecoration(
                                hintText: 'Filtrar por pacote, componente ou texto...',
                                prefixIcon: const Icon(Icons.search),
                                filled: true,
                                fillColor: const Color(0xFF0F172A),
                                contentPadding: const EdgeInsets.symmetric(horizontal: 16),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(12),
                                  borderSide: BorderSide.none,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        child: filtered.isEmpty
                            ? Center(
                                child: Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(
                                      Icons.radar_outlined,
                                      size: 64,
                                      color: Colors.white.withOpacity(0.2),
                                    ),
                                    const SizedBox(height: 16),
                                    Text(
                                      _logs.isEmpty
                                          ? 'Nenhum log no cache local.\n(Navegue nos apps monitorados para coletar)'
                                          : 'Nenhum log corresponde ao filtro.',
                                      textAlign: TextAlign.center,
                                      style: TextStyle(color: Colors.white.withOpacity(0.5)),
                                    ),
                                    if (_logs.isEmpty) ...[
                                      const SizedBox(height: 24),
                                      ElevatedButton.icon(
                                        onPressed: _openAccessibilitySettings,
                                        icon: const Icon(Icons.accessibility_new),
                                        label: const Text('Ativar Acessibilidade'),
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: const Color(0xFF06B6D4),
                                          foregroundColor: Colors.white,
                                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(12),
                                          ),
                                        ),
                                      )
                                    ]
                                  ],
                                ),
                              )
                            : ListView.builder(
                                itemCount: filtered.length,
                                itemBuilder: (context, index) {
                                  final log = filtered[index];
                                  return LogCard(
                                    log: log,
                                    onInspect: () => _showTreeDetails(log),
                                  );
                                },
                              ),
                      ),
                    ],
                  ),

                  // Tab 2: Logs de Envio (Histórico)
                  _uploadHistory.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.cloud_off_outlined,
                                size: 64,
                                color: Colors.white.withOpacity(0.2),
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'Nenhum arquivo enviado ao servidor ainda.\nOs envios de fim do dia aparecerão aqui.',
                                textAlign: TextAlign.center,
                                style: TextStyle(color: Colors.white.withOpacity(0.5)),
                              ),
                            ],
                          ),
                        )
                      : ListView.builder(
                          itemCount: _uploadHistory.length,
                          itemBuilder: (context, index) {
                            final item = _uploadHistory[index];
                            final isSuccess = item.status == 'SUCESSO';
                            final timeStr =
                                '${item.timestamp.hour.toString().padLeft(2, '0')}:${item.timestamp.minute.toString().padLeft(2, '0')}:${item.timestamp.second.toString().padLeft(2, '0')}';

                            return Card(
                              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                                side: BorderSide(
                                  color: isSuccess ? const Color(0xFF10B981).withOpacity(0.2) : Colors.redAccent.withOpacity(0.2),
                                  width: 1,
                                ),
                              ),
                              child: ExpansionTile(
                                leading: Icon(
                                  isSuccess ? Icons.cloud_done : Icons.error_outline,
                                  color: isSuccess ? const Color(0xFF10B981) : Colors.redAccent,
                                  size: 32,
                                ),
                                title: Text(
                                  item.filename,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 13,
                                    fontFamily: 'monospace',
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                                subtitle: Text(
                                  'Status: ${item.status} · $timeStr · ${item.recordCount} telas',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.5),
                                    fontSize: 11,
                                  ),
                                ),
                                children: [
                                  Padding(
                                    padding: const EdgeInsets.all(16),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const Divider(height: 1, color: Colors.white10),
                                        const SizedBox(height: 12),
                                        const Text(
                                          'RESPOSTA DO SERVIDOR:',
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.bold,
                                            color: Color(0xFF06B6D4),
                                          ),
                                        ),
                                        const SizedBox(height: 8),
                                        Container(
                                          width: double.infinity,
                                          padding: const EdgeInsets.all(12),
                                          decoration: BoxDecoration(
                                            color: const Color(0xFF050B14),
                                            borderRadius: BorderRadius.circular(8),
                                            border: Border.all(color: Colors.white10),
                                          ),
                                          child: SelectableText(
                                            item.responseMessage,
                                            style: const TextStyle(
                                              fontFamily: 'monospace',
                                              fontSize: 11,
                                              color: Color(0xFFE2E8F0),
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class LogCard extends StatefulWidget {
  final LogItem log;
  final VoidCallback onInspect;

  const LogCard({
    super.key,
    required this.log,
    required this.onInspect,
  });

  @override
  State<LogCard> createState() => _LogCardState();
}

class _LogCardState extends State<LogCard> {
  bool _isCardExpanded = false;
  bool _isTextsExpanded = false;

  @override
  Widget build(BuildContext context) {
    final log = widget.log;
    final timeStr =
        '${log.timestamp.hour.toString().padLeft(2, '0')}:${log.timestamp.minute.toString().padLeft(2, '0')}:${log.timestamp.second.toString().padLeft(2, '0')}';

    const int maxInitialTextItems = 5;
    final bool hasMoreTexts = log.flatTexts.length > maxInitialTextItems;
    final displayTexts = _isTextsExpanded
        ? log.flatTexts
        : log.flatTexts.take(maxInitialTextItems).toList();

    return Card(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.white.withOpacity(0.05)),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          initiallyExpanded: false,
          onExpansionChanged: (expanded) {
            setState(() {
              _isCardExpanded = expanded;
            });
          },
          leading: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF06B6D4).withOpacity(0.15), // Cyan 500
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              log.eventType.replaceFirst('TYPE_', '').split('_').last,
              style: const TextStyle(
                color: Color(0xFF06B6D4),
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          title: Text(
            log.packageName,
            style: const TextStyle(
              color: Colors.white70,
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
            overflow: TextOverflow.ellipsis,
          ),
          subtitle: Text(
            'Layout com ${log.flatTexts.length} textos · $timeStr',
            style: TextStyle(
              color: Colors.white.withOpacity(0.4),
              fontSize: 11,
            ),
          ),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Divider(height: 1, color: Colors.white10),
                  const SizedBox(height: 12),
                  Text(
                    'Classe Raiz: ${log.className}',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (log.flatTexts.isNotEmpty) ...[
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Textos Identificados:',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: Colors.white60,
                          ),
                        ),
                        if (hasMoreTexts)
                          GestureDetector(
                            onTap: () {
                              setState(() {
                                _isTextsExpanded = !_isTextsExpanded;
                              });
                            },
                            child: Text(
                              _isTextsExpanded ? 'Recolher textos' : 'Ver todos (${log.flatTexts.length})',
                              style: const TextStyle(
                                fontSize: 11,
                                color: Color(0xFF06B6D4),
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        ...displayTexts.map((text) {
                          return Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.05),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              text.length > 40 ? '${text.substring(0, 37)}...' : text,
                              style: const TextStyle(fontSize: 12, color: Color(0xFFE2E8F0)),
                            ),
                          );
                        }),
                        if (!_isTextsExpanded && hasMoreTexts)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: const Color(0xFF06B6D4).withOpacity(0.1),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              '+${log.flatTexts.length - maxInitialTextItems} itens...',
                              style: const TextStyle(fontSize: 12, color: Color(0xFF06B6D4), fontWeight: FontWeight.bold),
                            ),
                          ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: widget.onInspect,
                          icon: const Icon(Icons.unfold_more, size: 16),
                          label: const Text('Inspecionar Árvore da Tela'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF0F172A),
                            foregroundColor: const Color(0xFF06B6D4),
                            side: const BorderSide(color: Color(0xFF06B6D4), width: 1),
                            elevation: 0,
                            padding: const EdgeInsets.symmetric(vertical: 12),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
