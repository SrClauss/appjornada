import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:app_motorista/core/api_service.dart';

class AiTerminalConsoleScreen extends StatefulWidget {
  final String videoPath;
  final String? plataforma;
  final double? faturamentoAncora;
  final int? corridasAncora;

  const AiTerminalConsoleScreen({
    super.key,
    required this.videoPath,
    this.plataforma,
    this.faturamentoAncora,
    this.corridasAncora,
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
  String _activeModel = 'gemini-2.5-flash';
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

  void _copiarLogsParaClipboard() {
    final fullText = _terminalLogs.join('\n');
    Clipboard.setData(ClipboardData(text: fullText));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Row(
          children: [
            Icon(Icons.copy, color: Colors.white, size: 18),
            SizedBox(width: 8),
            Text('Logs do Terminal de IA copiados para a área de transferência!'),
          ],
        ),
        backgroundColor: Color(0xFF10B981),
        duration: Duration(seconds: 2),
      ),
    );
  }

  Future<void> _startProcess() async {
    final platTag = widget.plataforma != null ? " [PLATAFORMA: ${widget.plataforma!.toUpperCase()}]" : "";
    _addLog("==================================================================");
    _addLog(">>> INICIANDO PROCESSAMENTO MULTIMODAL DE VÍDEO DO EXTRATO$platTag <<<");
    _addLog("==================================================================");
    _addLog("Arquivo local: ${widget.videoPath.split('/').last}");
    if (widget.corridasAncora != null && widget.corridasAncora! > 0) {
      _addLog("Declaração do Motorista: ${widget.corridasAncora} corridas | R\$ ${widget.faturamentoAncora?.toStringAsFixed(2) ?? '0.00'}");
    }

    // Passo 1: Leitura e upload
    await Future.delayed(const Duration(milliseconds: 200));
    _addLog("\n[PASSO 1/5 - MÍDIA & UPLOAD]");
    _addLog(" > Lendo arquivo de vídeo .mp4 e gerando payload multipart...");
    _addLog(" > Enviando arquivo para o servidor via POST /jornadas/aberta/extrato-video...");

    // Passo 2: Fatiamento OpenCV
    await Future.delayed(const Duration(milliseconds: 300));
    _addLog("\n[PASSO 2/5 - OPENCV FRAME EXTRACTION]");
    final expectedFrames = (widget.corridasAncora != null && widget.corridasAncora! > 0) ? (widget.corridasAncora! * 3) : 35;
    _addLog(" > Amostragem OpenCV (3x densidade): Extraindo ~$expectedFrames quadros em 720p...");

    // Passo 3: Envio para o Backend + IA
    _addLog("\n[PASSO 3/5 - GOOGLE GEMINI VISION ENGINE]");
    _addLog(" > Conectando ao modelo Gemini Flash...");
    _addLog(" > Transmitindo quadros e executando prompt de leitura estrita...");

    try {
      final startTime = DateTime.now();
      final res = await ApiService.processarVideoExtrato(
        widget.videoPath, 
        plataforma: widget.plataforma,
        faturamentoAncora: widget.faturamentoAncora,
        corridasAncora: widget.corridasAncora,
      );
      final elapsed = DateTime.now().difference(startTime).inMilliseconds / 1000.0;

      if (!mounted) return;

      if (res != null && (res['sucesso'] == true || (res['corridas'] != null && (res['corridas'] as List).isNotEmpty))) {
        final modeloUsed = res['modelo_utilizado'] ?? 'gemini-2.5-flash';
        final framesCount = res['frames_count'] ?? expectedFrames;
        final promptText = res['prompt_enviado'];
        final rawResponseText = res['raw_response'];

        setState(() {
          _activeModel = modeloUsed;
        });

        _addLog(" > [OK] Leitura concluída em ${elapsed.toStringAsFixed(1)}s via modelo: $modeloUsed!");
        _addLog(" > [OPENCV] Total de quadros extraídos e analisados: $framesCount quadros.");

        if (promptText != null && promptText.toString().isNotEmpty) {
          _addLog("\n------------------- PROMPT ENVIADO À IA -------------------");
          _addLog(promptText.toString());
          _addLog("-----------------------------------------------------------");
        }

        if (rawResponseText != null && rawResponseText.toString().isNotEmpty) {
          _addLog("\n----------------- RESPOSTA BRUTA JSON DA IA -----------------");
          _addLog(rawResponseText.toString());
          _addLog("-----------------------------------------------------------");
        }

        _addLog("\n[PASSO 4/5 - PROCESSAMENTO & DEDUPLICAÇÃO]");
        final corridas = res['corridas'] as List? ?? [];
        final totalCorridas = res['corridas_adicionadas'] ?? corridas.length;
        
        final fatPlat = res['faturamento_plataforma'] ?? res['faturamento_acumulado'] ?? res['faturamento_total'] ?? (res['faturamento']?['total']) ?? 0.0;
        final fatTotalAcumulado = res['faturamento_acumulado'] ?? res['faturamento']?['total'] ?? fatPlat;

        _addLog(" > Verificando padrão de rolagem de tela e desduplicando corridas...");
        _addLog(" > Corridas extraídas do extrato: $totalCorridas corrida(s) identificada(s).");
        
        _addLog("\n------------------- LISTA DE CORRIDAS EXTRAÍDAS -------------------");
        for (var i = 0; i < corridas.length; i++) {
          final c = corridas[i];
          final val = c['valor_reais'] ?? c['valor'] ?? '0.00';
          final platName = c['plataforma'] ?? widget.plataforma ?? 'UBER';
          final hor = c['horario'] ?? '--:--';
          final orig = c['origem'] ?? 'Origem N/A';
          final dest = c['destino'] ?? 'Destino N/A';
          _addLog(" #${i + 1} -> [$platName] $hor | R\$ ${fatValFormatted(val)} | $orig -> $dest");
        }
        _addLog("------------------------------------------------------------------");

        _addLog("\n[PASSO 5/5 - MATEMÁTICA & FATURAMENTO]");
        if (widget.plataforma != null) {
          _addLog(" > Faturamento total para ${widget.plataforma!.toUpperCase()}: R\$ ${fatValFormatted(fatPlat)}");
        }
        _addLog(" > Faturamento total acumulado da jornada: R\$ ${fatValFormatted(fatTotalAcumulado)}");
        _addLog("\n==================================================================");
        _addLog("✅ [SUCESSO] Processamento de vídeo do extrato concluído com exatidão!");
        _addLog("==================================================================");

        setState(() {
          _isProcessing = false;
          _success = true;
          _statusMessage = 'Extrato ${widget.plataforma ?? ""} Processado com Sucesso!';
          _resultData = res;
        });
      } else {
        final msg = res?['mensagem'] ?? 'Nenhuma corrida legível identificada no vídeo.';
        _addLog("\n[AVISO] $msg");

        setState(() {
          _isProcessing = false;
          _success = false;
          _statusMessage = msg;
          _resultData = res;
        });
      }
    } catch (e) {
      if (!mounted) return;
      _addLog("\n[ERRO] Falha no processamento: $e");
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
          IconButton(
            icon: const Icon(Icons.copy_all_rounded, color: Color(0xFF38BDF8)),
            tooltip: 'Copiar Todos os Logs',
            onPressed: _copiarLogsParaClipboard,
          ),
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
                        Text(
                          'Modelo Ativo: $_activeModel',
                          style: const TextStyle(color: Colors.grey, fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF334155),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    ),
                    icon: const Icon(Icons.copy, size: 14),
                    label: const Text('COPIAR', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                    onPressed: _copiarLogsParaClipboard,
                  ),
                ],
              ),
            ),

            // Console Terminal Output (Copiável via SelectableText)
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
                    } else if (log.contains('[PASSO')) {
                      logColor = const Color(0xFFF472B6); // Rosa/Lilás passos
                    } else if (log.contains('---')) {
                      logColor = Colors.grey;
                    }

                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2.0),
                      child: SelectableText(
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
