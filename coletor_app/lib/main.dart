import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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

  LogItem({
    required this.timestamp,
    required this.packageName,
    required this.className,
    required this.eventType,
    required this.tree,
    required this.flatTexts,
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
  String _searchQuery = '';
  bool _isPaused = false;

  @override
  void initState() {
    super.initState();
    _startListening();
  }

  @override
  void dispose() {
    _stopListening();
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

        setState(() {
          _logs.insert(
            0,
            LogItem(
              timestamp: DateTime.now(),
              packageName: data['packageName'] ?? '',
              className: data['className'] ?? '',
              eventType: data['eventType'] ?? '',
              tree: tree,
              flatTexts: flatTexts,
            ),
          );
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

    return Scaffold(
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
            tooltip: 'Configurações de Acessibilidade',
            icon: const Icon(Icons.settings, color: Color(0xFF06B6D4)),
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
      ),
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            color: const Color(0xFF1E293B),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Telas Capturadas: ${_logs.length}',
                      style: const TextStyle(fontWeight: FontWeight.w500),
                    ),
                    Row(
                      children: [
                        const Text('Pausar captura'),
                        Switch(
                          value: _isPaused,
                          activeColor: const Color(0xFF10B981),
                          onChanged: (val) {
                            setState(() {
                              _isPaused = val;
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
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

// Widget Stateful para gerenciar o estado recolhido/expandido de cada card de log individualmente
class LogCard extends StatefulWidget {
  final LogItem log;
  final VoidCallback onInspect;

  const LogCard({super.key, required this.log, required this.onInspect});

  @override
  State<LogCard> createState() => _LogCardState();
}

class _LogCardState extends State<LogCard> with SingleTickerProviderStateMixin {
  bool _isCardExpanded = false;
  bool _isTextsExpanded = false;

  @override
  Widget build(BuildContext context) {
    final log = widget.log;
    final timeStr =
        '${log.timestamp.hour.toString().padLeft(2, '0')}:${log.timestamp.minute.toString().padLeft(2, '0')}:${log.timestamp.second.toString().padLeft(2, '0')}';

    // Estimativa: mostramos no máximo 5 itens (aproximadamente 2 linhas de Tags) antes de exigir expansão
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
        // Remove bordas extras que o ExpansionTile coloca por padrão
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
          title: Text(
            log.packageName,
            style: const TextStyle(
              color: Color(0xFF06B6D4),
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
