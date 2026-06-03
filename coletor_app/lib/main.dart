import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

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

  // Configurações do Servidor
  final TextEditingController _urlController = TextEditingController(text: 'http://2.24.121.189:3000/api');
  final TextEditingController _keyController = TextEditingController(text: 'coleta-dev-key');
  final TextEditingController _deviceController = TextEditingController(text: 'Celular Cláudio');
  bool _autoUpload = true; // Ativo por padrão
  bool _isSyncing = false;
  bool _showSettings = false;

  @override
  void initState() {
    super.initState();
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

        setState(() {
          _logs.insert(0, newLog);
        });

        if (_autoUpload) {
          _uploadSingleLog(newLog);
        }
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

  Future<bool> _uploadToServer(List<LogItem> logsToUpload) async {
    if (logsToUpload.isEmpty) return true;

    final int recordCount = logsToUpload.length;
    final String package = logsToUpload.length == 1 ? logsToUpload.first.packageName : 'coleta_lote';
    final String dateStr = DateTime.now().toIso8601String().replaceAll(':', '-');
    final String filename = "${package}_$dateStr.jsonl";

    try {
      final String jsonlContent = logsToUpload.map((log) {
        return jsonEncode({
          "timestamp": log.timestamp.toIso8601String(),
          "packageName": log.packageName,
          "activityClass": log.className,
          "eventType": log.eventType,
          "tree": log.tree,
        });
      }).join('\n') + '\n';

      final String baseUrl = _urlController.text.trim();
      final Uri uri = Uri.parse("$baseUrl/coleta/upload");

      final request = http.MultipartRequest('POST', uri);
      request.headers['x-api-key'] = _keyController.text.trim();

      final file = http.MultipartFile.fromBytes(
        'arquivo',
        utf8.encode(jsonlContent),
        filename: filename,
      );
      request.files.add(file);

      final deviceName = _deviceController.text.trim();
      if (deviceName.isNotEmpty) {
        request.fields['dispositivo'] = deviceName;
      }

      final response = await request.send();
      final body = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        setState(() {
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
        return true;
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
        return false;
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
      return false;
    }
  }

  Future<void> _uploadSingleLog(LogItem log) async {
    final success = await _uploadToServer([log]);
    if (success) {
      setState(() {
        log.isSynced = true;
      });
    }
  }

  Future<void> _syncAllUnsynced() async {
    final unsynced = _logs.where((log) => !log.isSynced).toList();
    if (unsynced.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Todos os logs já estão no servidor!')),
      );
      return;
    }

    setState(() {
      _isSyncing = true;
    });

    final success = await _uploadToServer(unsynced);

    setState(() {
      _isSyncing = false;
      if (success) {
        for (var log in unsynced) {
          log.isSynced = true;
        }
      }
    });

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          success
              ? '${unsynced.length} logs sincronizados com sucesso!'
              : 'Falha ao sincronizar logs com o servidor.',
        ),
        backgroundColor: success ? Colors.green : Colors.red,
      ),
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
    final int unsyncedCount = _logs.where((log) => !log.isSynced).length;

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
              tooltip: 'Configurações do Servidor',
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
              tooltip: 'Limpar Logs',
              icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
              onPressed: () {
                setState(() {
                  _logs.clear();
                });
              },
            ),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.radar), text: 'Layouts da Tela'),
              Tab(icon: Icon(Icons.cloud_sync), text: 'Envios para o Servidor'),
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
                    const SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Sincronizar em Tempo Real (Upload Automático)'),
                        Switch(
                          value: _autoUpload,
                          activeColor: const Color(0xFF10B981),
                          onChanged: (val) {
                            setState(() {
                              _autoUpload = val;
                            });
                          },
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
                  // Tab 1: Layouts da Tela (Radar de Captura)
                  Column(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(16),
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
                                      'Telas Capturadas: ${_logs.length}',
                                      style: const TextStyle(fontWeight: FontWeight.w500),
                                    ),
                                    if (unsyncedCount > 0)
                                      Text(
                                        '$unsyncedCount logs pendentes de nuvem',
                                        style: const TextStyle(fontSize: 12, color: Colors.amberAccent),
                                      )
                                    else
                                      const Text(
                                        'Tudo sincronizado',
                                        style: TextStyle(fontSize: 12, color: Color(0xFF10B981)),
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
                                    else if (unsyncedCount > 0)
                                      ElevatedButton.icon(
                                        onPressed: _syncAllUnsynced,
                                        icon: const Icon(Icons.sync, size: 16),
                                        label: const Text('Sincronizar'),
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: const Color(0xFF06B6D4),
                                          foregroundColor: Colors.white,
                                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
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
                            const SizedBox(height: 8),
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
                                          ? 'Aguardando layouts estruturados...\n(Abra e navegue no GitHub, Uber ou 99)'
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
                                          backgroundColor: const Color(0xFF10B981),
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
                                    onSync: () => _uploadSingleLog(log),
                                  );
                                },
                              ),
                      ),
                    ],
                  ),

                  // Tab 2: Logs de Envio (Histórico de Envios para a Nuvem)
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
                                'Nenhum arquivo enviado ao servidor ainda.\nOs envios automáticos ou manuais aparecerão aqui.',
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
  final VoidCallback onSync;

  const LogCard({
    super.key,
    required this.log,
    required this.onInspect,
    required this.onSync,
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
              color: const Color(0xFF10B981).withOpacity(0.15),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              log.eventType.replaceFirst('TYPE_', '').split('_').last,
              style: const TextStyle(
                color: Color(0xFF10B981),
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          title: Row(
            children: [
              Expanded(
                child: Text(
                  log.packageName,
                  style: const TextStyle(
                    color: Color(0xFF06B6D4),
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Icon(
                log.isSynced ? Icons.cloud_done : Icons.cloud_queue,
                size: 16,
                color: log.isSynced ? const Color(0xFF10B981) : Colors.white30,
              ),
            ],
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
                      if (!log.isSynced) ...[
                        const SizedBox(width: 8),
                        IconButton(
                          tooltip: 'Enviar este log agora',
                          icon: const Icon(Icons.cloud_upload, color: Color(0xFF10B981)),
                          onPressed: widget.onSync,
                        ),
                      ]
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
