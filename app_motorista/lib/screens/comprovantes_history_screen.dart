import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:app_motorista/core/api_service.dart';

class ComprovantesHistoryScreen extends StatefulWidget {
  final Map<String, dynamic> jornada;
  final Function(Map<String, dynamic>) onJornadaUpdated;
  final VoidCallback onBack;

  const ComprovantesHistoryScreen({
    super.key,
    required this.jornada,
    required this.onJornadaUpdated,
    required this.onBack,
  });

  @override
  State<ComprovantesHistoryScreen> createState() => _ComprovantesHistoryScreenState();
}

class _ComprovantesHistoryScreenState extends State<ComprovantesHistoryScreen> {
  bool _loading = false;

  String _getFullUrl(String? url) {
    if (url == null) return '';
    if (url.startsWith('http')) return url;
    final base = ApiService.baseUrl.replaceAll('/api', '');
    return '$base$url';
  }

  Future<void> _refreshJornada() async {
    setState(() {
      _loading = true;
    });
    try {
      final res = await http.get(
        Uri.parse('${ApiService.baseUrl}/jornadas/aberta'),
        headers: ApiService.headers,
      );
      if (res.statusCode == 200) {
        final updated = json.decode(res.body);
        widget.onJornadaUpdated(updated);
      }
    } catch (e) {
      print('[ComprovantesHistoryScreen] Erro ao recarregar jornada: $e');
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _deletarComprovante(String url) async {
    setState(() {
      _loading = true;
    });
    try {
      final res = await ApiService.deletarComprovante(url);
      if (res != null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Comprovante excluído com sucesso.'), backgroundColor: Colors.green),
          );
        }
        await _refreshJornada();
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Erro ao excluir comprovante no servidor.'), backgroundColor: Colors.red),
          );
        }
      }
    } catch (e) {
      print('[ComprovantesHistoryScreen] Erro ao deletar: $e');
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _uploadNovoComprovante() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery);
    if (picked == null) return;

    setState(() {
      _loading = true;
    });

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enviando print de comprovante para a IA...'), duration: Duration(seconds: 4)),
      );
    }

    try {
      final res = await ApiService.uploadAndProcessComprovante(picked.path);
      if (res != null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Print processado com sucesso!'), backgroundColor: Colors.green),
          );
        }
        await _refreshJornada();
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Erro de processamento da IA. Verifique se o print é legível e tente novamente.'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      print('[ComprovantesHistoryScreen] Erro no upload: $e');
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  void _mostrarImagemZoom(String url) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(8),
        child: Stack(
          alignment: Alignment.center,
          children: [
            Container(
              color: Colors.black87,
              width: double.infinity,
              height: double.infinity,
              child: InteractiveViewer(
                minScale: 0.5,
                maxScale: 4.0,
                child: Image.network(
                  url,
                  fit: BoxFit.contain,
                  errorBuilder: (ctx, err, stack) => const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.broken_image, color: Colors.redAccent, size: 64),
                        SizedBox(height: 12),
                        Text('Erro ao carregar comprovante', style: TextStyle(color: Colors.white70)),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            Positioned(
              top: 16,
              right: 16,
              child: CircleAvatar(
                backgroundColor: Colors.black54,
                child: IconButton(
                  icon: const Icon(Icons.close, color: Colors.white),
                  onPressed: () => Navigator.pop(context),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final faturamento = widget.jornada['faturamento'] ?? {};
    final list = faturamento['comprovantes_processados'] as List? ?? [];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Prints de Faturamento'),
        backgroundColor: const Color(0xFF1E293B),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: widget.onBack,
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshJornada,
          ),
        ],
      ),
      body: Stack(
        children: [
          RefreshIndicator(
            onRefresh: _refreshJornada,
            child: list.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: [
                      SizedBox(height: MediaQuery.of(context).size.height * 0.25),
                      const Center(
                        child: Column(
                          children: [
                            Icon(Icons.image_not_supported_outlined, size: 72, color: Colors.grey),
                            SizedBox(height: 16),
                            Text(
                              'Nenhum print enviado hoje.',
                              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white70),
                            ),
                            SizedBox(height: 8),
                            Padding(
                              padding: EdgeInsets.symmetric(horizontal: 40.0),
                              child: Text(
                                'Use o balão flutuante para capturar prints de faturamento enquanto trabalha.',
                                style: TextStyle(color: Colors.grey, fontSize: 13),
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(16.0),
                    itemCount: list.length,
                    itemBuilder: (context, index) {
                      final item = list[index] as Map<String, dynamic>;
                      final String plataforma = item['plataforma'] ?? 'OUTROS';
                      final double valor = (item['valor'] ?? 0.0).toDouble();
                      final String? origem = item['origem'];
                      final String? destino = item['destino'];
                      final String? dataHora = item['data_hora'];
                      final String url = item['url_comprovante'] ?? '';

                      final bool isIncompleto = valor == 0.0 || plataforma == 'OUTROS';

                      return Card(
                        margin: const EdgeInsets.only(bottom: 16.0),
                        color: const Color(0xFF1E293B),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        child: Padding(
                          padding: const EdgeInsets.all(12.0),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // Miniatura da Imagem
                              GestureDetector(
                                onTap: () => _mostrarImagemZoom(_getFullUrl(url)),
                                child: Container(
                                  width: 80,
                                  height: 120,
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(color: Colors.white12),
                                  ),
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: url.isNotEmpty
                                        ? Image.network(
                                            _getFullUrl(url),
                                            fit: BoxFit.cover,
                                            errorBuilder: (ctx, err, stack) => const Center(
                                              child: Icon(Icons.broken_image, color: Colors.redAccent),
                                            ),
                                          )
                                        : const Center(child: Icon(Icons.image, color: Colors.grey)),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              // Detalhes do Faturamento
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                          decoration: BoxDecoration(
                                            color: plataforma == 'UBER'
                                                ? Colors.blue.withOpacity(0.2)
                                                : plataforma == '99'
                                                    ? Colors.yellow.withOpacity(0.2)
                                                    : Colors.grey.withOpacity(0.2),
                                            borderRadius: BorderRadius.circular(6),
                                          ),
                                          child: Text(
                                            plataforma,
                                            style: TextStyle(
                                              fontWeight: FontWeight.bold,
                                              fontSize: 12,
                                              color: plataforma == 'UBER'
                                                  ? Colors.blue
                                                  : plataforma == '99'
                                                      ? Colors.yellowAccent
                                                      : Colors.grey,
                                            ),
                                          ),
                                        ),
                                        Text(
                                          'R\$ ${valor.toStringAsFixed(2)}',
                                          style: const TextStyle(
                                            fontWeight: FontWeight.bold,
                                            fontSize: 16,
                                            color: Colors.greenAccent,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 8),
                                    Row(
                                      children: [
                                        Icon(
                                          isIncompleto ? Icons.warning_amber_rounded : Icons.check_circle_outline,
                                          size: 14,
                                          color: isIncompleto ? Colors.orangeAccent : Colors.green,
                                        ),
                                        const SizedBox(width: 4),
                                        Text(
                                          isIncompleto ? 'Dados Incompletos / Não Identificados' : 'Lido e Processado',
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.bold,
                                            color: isIncompleto ? Colors.orangeAccent : Colors.green,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 8),
                                    if (dataHora != null && dataHora.isNotEmpty)
                                      Padding(
                                        padding: const EdgeInsets.only(bottom: 4.0),
                                        child: Text(
                                          'Data/Hora: $dataHora',
                                          style: const TextStyle(fontSize: 11, color: Colors.grey),
                                        ),
                                      ),
                                    if (origem != null && origem.isNotEmpty)
                                      Padding(
                                        padding: const EdgeInsets.only(bottom: 4.0),
                                        child: Text(
                                          'De: $origem',
                                          style: const TextStyle(fontSize: 11, color: Colors.white70),
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    if (destino != null && destino.isNotEmpty)
                                      Text(
                                        'Para: $destino',
                                        style: const TextStyle(fontSize: 11, color: Colors.white70),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
          if (_loading)
            Container(
              color: Colors.black54,
              child: const Center(
                child: CircularProgressIndicator(),
              ),
            ),
        ],
      ),
    );
  }
}
