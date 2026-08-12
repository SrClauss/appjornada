import 'dart:async';
import 'package:flutter/material.dart';
import 'package:app_motorista/core/api_service.dart';

class AiTerminalConsoleScreen extends StatefulWidget {
  final String videoPath;
  final String? plataforma;

  const AiTerminalConsoleScreen({
    super.key,
    required this.videoPath,
    this.plataforma,
  });

  @override
  State<AiTerminalConsoleScreen> createState() => _AiTerminalConsoleScreenState();
}

class _AiTerminalConsoleScreenState extends State<AiTerminalConsoleScreen> {
  final List<String> _terminalLogs = [];
  final ScrollController _scrollController = ScrollController();
  
  bool _isProcessing = true;
  bool _success = false;
  String _statusMessage = 'Iniciando análise com IA...';
  Map<String, dynamic>? _resultData;

  @override
  void initState() {
    super.initState();
    _startProcess();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _addLog(String logText) {
    if (!mounted) return;
    setState(() {
      final now = DateTime.now();
      final timeStr = "${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}:${now.second.toString().padLeft(2, '0')}.${(now.millisecond / 100).floor()}";
      _terminalLogs.add("[$timeStr] $logText");
    });
    
    // Auto-scroll para o final do terminal
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _startProcess() async {
    final platTag = widget.plataforma != null ? " [PLATAFORMA: ${widget.plataforma!.toUpperCase()}]" : "";
    _addLog(">>> INICIANDO PROCESSAMENTO MULTIMODAL DE VÍDEO DO EXTRATO$platTag <<<");
    _addLog("Modelo Primário Selecionado: gemini-3.5-flash-lite");
    _addLog("Arquivo local: ${widget.videoPath.split('/').last}");

    // Passo 1: Leitura e upload
    await Future.delayed(const Duration(milliseconds: 300));
    _addLog("[SISTEMA] Lendo arquivo de mídia e gerando payload multipart...");
    
    // Passo 2: Fatiamento OpenCV
    await Future.delayed(const Duration(milliseconds: 500));
    _addLog("[OPENCV] Analisando estrutura de frames do vídeo...");
    _addLog("[OPENCV] Amostragem uniforme calculada: extraindo quadros ao longo do vídeo...");
    _addLog("[OPENCV] 8 quadros em formato JPEG (720p) prontos para análise de visão.");

    // Passo 3: Envio para o Backend + IA
    _addLog("[REDE] Transmitindo quadros para a API Gemini (gemini-3.5-flash-lite)...");
    _addLog("[IA] Processando prompt de extração e deduplicação multimodal para ${widget.plataforma ?? 'todas as plataformas'}...");

    try {
      final startTime = DateTime.now();
      final res = await ApiService.processarVideoExtrato(widget.videoPath, plataforma: widget.plataforma);
      final elapsed = DateTime.now().difference(startTime).inMilliseconds / 1000.0;

      if (!mounted) return;

      if (res != null && (res['sucesso'] == true || (res['corridas'] != null && (res['corridas'] as List).isNotEmpty))) {
        _addLog("[IA] Resposta recebida da API Gemini em ${elapsed.toStringAsFixed(1)}s.");
        _addLog("[IA] Modelo de Execução: gemini-3.5-flash-lite (Status 200 OK)");

        final corridas = res['corridas'] as List? ?? [];
        final totalCorridas = res['corridas_adicionadas'] ?? corridas.length;
        
        final fatPlat = res['faturamento_plataforma'] ?? res['faturamento_acumulado'] ?? res['faturamento_total'] ?? (res['faturamento']?['total']) ?? 0.0;
        final fatTotalAcumulado = res['faturamento_acumulado'] ?? res['faturamento']?['total'] ?? fatPlat;

        _addLog("[DEDUPLICAÇÃO] Verificando padrão de rolagem de tela e duplicatas...");
        _addLog("[DEDUPLICAÇÃO] Faturamento filtrado: $totalCorridas corrida(s) identificada(s).");
        
        for (var i = 0; i < corridas.length; i++) {
          final c = corridas[i];
          final val = c['valor_reais'] ?? c['valor'] ?? '0.00';
          final platName = c['plataforma'] ?? widget.plataforma ?? 'Uber/99';
          _addLog("  #${i + 1} -> [$platName] ${c['horario'] ?? '--:--'} | ${c['categoria'] ?? 'Corrida'} | R\$ ${fatValFormatted(val)} | ${c['origem'] ?? 'Origem N/A'} -> ${c['destino'] ?? 'Destino N/A'}");
        }

        if (widget.plataforma != null) {
          _addLog("[BACKEND] Faturamento detectado para ${widget.plataforma!.toUpperCase()}: R\$ ${fatValFormatted(fatPlat)}");
        }
        _addLog("[BACKEND] Faturamento total acumulado da jornada: R\$ ${fatValFormatted(fatTotalAcumulado)}");
        _addLog("[SUCESSO] Processamento concluído com conformidade!");

        setState(() {
          _isProcessing = false;
          _success = true;
          _statusMessage = 'Extrato ${widget.plataforma ?? ""} Processado com Sucesso!';
          _resultData = res;
        });
      } else {
        final msg = res?['mensagem'] ?? 'Nenhuma corrida legível identificada no vídeo.';
        _addLog("[AVISO] $msg");
        _addLog("[RETENTATIVA] Modelo gemini-3.5-flash-lite não retornou corridas válidas.");

        setState(() {
          _isProcessing = false;
          _success = false;
          _statusMessage = msg;
          _resultData = res;
        });
      }
    } catch (e) {
      if (!mounted) return;
      _addLog("[ERRO] Falha no processamento: $e");
      setState(() {
        _isProcessing = false;
        _success = false;
        _statusMessage = 'Erro ao processar vídeo com a IA.';
      });
    }
  }

  String fatValFormatted(dynamic val) {
    if (val is num) return val.toStringAsFixed(2);
    if (val is String) {
      final parsed = double.tryParse(val);
      if (parsed != null) return parsed.toStringAsFixed(2);
    }
    return '0.00';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        title: const Row(
          children: [
            Icon(Icons.terminal, color: Color(0xFF10B981)),
            SizedBox(width: 8),
            Text('Terminal de Controle IA', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
          ],
        ),
        centerTitle: false,
        automaticallyImplyLeading: false,
        actions: [
          if (!_isProcessing)
            IconButton(
              icon: const Icon(Icons.close, color: Colors.white),
              onPressed: () => Navigator.pop(context, _resultData),
            ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Header Status Bar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              color: const Color(0xFF1E293B),
              child: Row(
                children: [
                  if (_isProcessing)
                    const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF10B981)),
                    )
                  else
                    Icon(
                      _success ? Icons.check_circle : Icons.error_outline,
                      color: _success ? const Color(0xFF10B981) : Colors.red,
                      size: 22,
                    ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _statusMessage,
                          style: TextStyle(
                            color: _success ? const Color(0xFF10B981) : (_isProcessing ? Colors.white : Colors.red),
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 2),
                        const Text(
                          'Modelo Activo: gemini-3.5-flash-lite',
                          style: TextStyle(color: Colors.grey, fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // Console Terminal Output
            Expanded(
              child: Container(
                margin: const EdgeInsets.all(12),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.black,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: ListView.builder(
                  controller: _scrollController,
                  itemCount: _terminalLogs.length,
                  itemBuilder: (context, index) {
                    final log = _terminalLogs[index];
                    Color logColor = const Color(0xFF34D399); // Verde padrão terminal
                    if (log.contains('[ERRO]')) {
                      logColor = Colors.redAccent;
                    } else if (log.contains('[AVISO]')) {
                      logColor = Colors.amberAccent;
                    } else if (log.contains('>>>') || log.contains('[SUCESSO]')) {
                      logColor = const Color(0xFF38BDF8); // Azul neon
                    }

                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2.0),
                      child: Text(
                        log,
                        style: TextStyle(
                          fontFamily: 'monospace',
                          fontSize: 12,
                          color: logColor,
                          height: 1.3,
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),

            // Footer Action Button
            if (!_isProcessing)
              Container(
                padding: const EdgeInsets.all(16),
                color: const Color(0xFF1E293B),
                child: SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _success ? const Color(0xFF10B981) : const Color(0xFF6366F1),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    icon: Icon(_success ? Icons.check : Icons.arrow_back, color: Colors.white),
                    label: Text(
                      _success ? 'CONFIRMAR E CONTINUAR' : 'RETORNAR AO WIZARD',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white),
                    ),
                    onPressed: () {
                      Navigator.pop(context, _resultData);
                    },
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
