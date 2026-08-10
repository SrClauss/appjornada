import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:app_motorista/core/api_service.dart';
import 'package:app_motorista/core/overlay_service.dart';
import 'package:app_motorista/screens/ai_terminal_console_screen.dart';
import 'package:geolocator/geolocator.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';


class FechamentoWizardScreen extends StatefulWidget {
  final Map<String, dynamic> jornada;
  final VoidCallback onCompleted;
  final VoidCallback onCancel;

  const FechamentoWizardScreen({
    super.key,
    required this.jornada,
    required this.onCompleted,
    required this.onCancel,
  });

  @override
  State<FechamentoWizardScreen> createState() => _FechamentoWizardScreenState();
}

class _FechamentoWizardScreenState extends State<FechamentoWizardScreen> with WidgetsBindingObserver {
  int _currentStep = 1; // 1: Uber, 2: 99, 3: Outros, 4: Auditoria & Fechamento
  bool _loading = false;
  
  bool _isRecording = false;
  String? _recordedVideoPath;
  Map<String, dynamic>? _faturamentoLocal;

  // Controllers para faturamento declarado
  final _uberValorCtrl = TextEditingController(text: '0.0');
  final _uberCorridasCtrl = TextEditingController(text: '0');
  final _99ValorCtrl = TextEditingController(text: '0.0');
  final _99CorridasCtrl = TextEditingController(text: '0');
  final _outrosValorCtrl = TextEditingController(text: '0.0');
  final _outrosCorridasCtrl = TextEditingController(text: '0');

  // Dados da auditoria
  Map<String, dynamic>? _auditoriaResult;

  // Fechamento Final
  final _kmFinalCtrl = TextEditingController();
  String? _fotoKmFinalUrl;

  bool _isAiProcessing = false;
  final List<String> _terminalLogs = [];
  Timer? _terminalTimer;

  void _startTerminalSimulation() {
    _terminalTimer?.cancel();
    setState(() {
      _isAiProcessing = true;
      _terminalLogs.clear();
      _terminalLogs.add(' > [SYS] Conectando ao terminal de IA Gemini 3.6...');
    });
    final messages = [
      ' > [NET] Uploading gravação de tela (.mp4) para o servidor...',
      ' > [CV2] Servidor extraindo quadros (frames) do vídeo...',
      ' > [AI] Enviando imagens para Google Gemini 3.6 Flash Engine...',
      ' > [VISION] Analisando extratos, valores e corridas...',
      ' > [DATA] Agrupando faturamento acumulado por plataforma...',
      ' > [AUDIT] Executando validações e reconciliação de dados...',
    ];
    int idx = 0;
    _terminalTimer = Timer.periodic(const Duration(milliseconds: 650), (t) {
      if (idx < messages.length) {
        if (mounted) {
          setState(() {
            _terminalLogs.add(messages[idx]);
          });
        }
        idx++;
      } else {
        t.cancel();
      }
    });
  }

  void _stopTerminalSimulation(bool success, String detailMessage) {
    _terminalTimer?.cancel();
    if (mounted) {
      setState(() {
        _isAiProcessing = false;
        if (success) {
          _terminalLogs.add(' > [OK] Processamento concluído com sucesso!');
          _terminalLogs.add(' > [RES] $detailMessage');
        } else {
          _terminalLogs.add(' > [ERR] $detailMessage');
        }
      });
    }
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _checkRecordedVideo();
  }

  @override
  void dispose() {
    _terminalTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    _uberValorCtrl.dispose();
    _uberCorridasCtrl.dispose();
    _99ValorCtrl.dispose();
    _99CorridasCtrl.dispose();
    _outrosValorCtrl.dispose();
    _outrosCorridasCtrl.dispose();
    _kmFinalCtrl.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _checkRecordedVideo();
    }
  }

  Future<void> _checkRecordedVideo() async {
    try {
      const channel = MethodChannel('com.srclauss.appjornada/overlay');
      final String? path = await channel.invokeMethod<String>('getLastRecordedVideo');
      if (path != null && path.isNotEmpty) {
        if (mounted) {
          setState(() {
            _recordedVideoPath = path;
            _isRecording = false;
          });
        }
      }
    } catch (_) {}
  }

  Future<void> _rodarAuditoria() async {
    setState(() {
      _loading = true;
    });

    try {
      final jId = widget.jornada['_id'] ?? widget.jornada['id'];
      
      final uberVal = double.tryParse(_uberValorCtrl.text) ?? 0.0;
      final uberCorr = int.tryParse(_uberCorridasCtrl.text) ?? 0;
      final ninetyNineVal = double.tryParse(_99ValorCtrl.text) ?? 0.0;
      final ninetyNineCorr = int.tryParse(_99CorridasCtrl.text) ?? 0;
      final outrosVal = double.tryParse(_outrosValorCtrl.text) ?? 0.0;
      final outrosCorr = int.tryParse(_outrosCorridasCtrl.text) ?? 0;

      final url = '${ApiService.baseUrl}/jornadas/$jId/validar-fechamento'
          '?faturamento_uber=$uberVal&corridas_uber=$uberCorr'
          '&faturamento_99=$ninetyNineVal&corridas_99=$ninetyNineCorr'
          '&faturamento_outros=$outrosVal&corridas_outros=$outrosCorr';

      final res = await http.post(
        Uri.parse(url),
        headers: ApiService.headers,
      );

      if (res.statusCode == 200) {
        setState(() {
          _auditoriaResult = json.decode(res.body);
        });
      } else {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erro ao validar faturamento: ${res.body}')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro de conexão: $e')),
      );
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  Future<void> _subirComprovanteDivergente(String platform) async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery);
    if (picked == null) return;

    setState(() {
      _loading = true;
    });

    try {
      final res = await ApiService.uploadAndProcessComprovante(picked.path, plataforma: platform);
      if (res != null) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Comprovante processado com sucesso!'), backgroundColor: Colors.green),
        );
        // Roda a auditoria novamente para atualizar os dados
        await _rodarAuditoria();
      } else {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Erro ao processar comprovante.'), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro de conexão: $e')),
      );
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  Future<void> _capturarFotoHodometro(ImageSource source) async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: source);
    if (picked == null) return;

    setState(() {
      _loading = true;
    });

    try {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Lendo hodômetro com IA Gemini 3.5...')),
        );
      }
      
      final res = await ApiService.processarFotoOdometro(picked.path, contexto: 'km_final');
      if (res != null) {
        final url = res['foto_url'];
        final kmLido = res['km_lido'];
        
        setState(() {
          if (url != null) _fotoKmFinalUrl = url;
          if (kmLido != null) {
            _kmFinalCtrl.text = (kmLido as num).toDouble().toStringAsFixed(1);
          }
        });
        
        if (mounted) {
          if (kmLido != null) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('IA Gemini leu ${(kmLido as num).toDouble().toStringAsFixed(1)} KM no hodômetro!'),
                backgroundColor: Colors.green,
              ),
            );
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Foto salva com sucesso! Digite a leitura do hodômetro abaixo.'),
                backgroundColor: Colors.blue,
              ),
            );
          }
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erro ao ler foto do hodômetro: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _finalizarJornada() async {
    if (_kmFinalCtrl.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, informe o KM final.')),
      );
      return;
    }
    final kmFinal = double.tryParse(_kmFinalCtrl.text);
    if (kmFinal == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('KM final inválido.')),
      );
      return;
    }

    final kmInicial = widget.jornada['km']?['inicial'] ?? 0.0;
    if (kmFinal < kmInicial) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('KM final não pode ser menor que o inicial ($kmInicial km)')),
      );
      return;
    }

    setState(() {
      _loading = true;
    });

    try {
      double lat = -20.219;
      double lon = -40.264;
      try {
        final pos = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 4),
        );
        lat = pos.latitude;
        lon = pos.longitude;
      } catch (_) {}

      final jId = widget.jornada['_id'] ?? widget.jornada['id'];
      
      final uberVal = double.tryParse(_uberValorCtrl.text) ?? 0.0;
      final uberCorr = int.tryParse(_uberCorridasCtrl.text) ?? 0;
      final ninetyNineVal = double.tryParse(_99ValorCtrl.text) ?? 0.0;
      final ninetyNineCorr = int.tryParse(_99CorridasCtrl.text) ?? 0;
      final outrosVal = double.tryParse(_outrosValorCtrl.text) ?? 0.0;
      final outrosCorr = int.tryParse(_outrosCorridasCtrl.text) ?? 0;

      final url = '${ApiService.baseUrl}/jornadas/$jId/fechar'
          '?km_final=$kmFinal'
          '&faturamento_uber=$uberVal&corridas_uber=$uberCorr'
          '&faturamento_99=$ninetyNineVal&corridas_99=$ninetyNineCorr'
          '&faturamento_outros=$outrosVal&corridas_outros=$outrosCorr'
          '&localizacao_lat=$lat&localizacao_lon=$lon';

      final requestBody = <String, dynamic>{};
      if (_fotoKmFinalUrl != null) {
        requestBody['foto_km_final_url'] = _fotoKmFinalUrl;
      }

      final res = await http.patch(
        Uri.parse(url),
        headers: ApiService.headers,
        body: json.encode(requestBody),
      );

      if (res.statusCode == 200 || res.statusCode == 409) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Jornada encerrada com sucesso!'), backgroundColor: Colors.green),
        );
        widget.onCompleted();
      } else {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erro ao fechar jornada: ${res.body}')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro de conexão: $e')),
      );
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: Text('Finalizar Jornada (Passo $_currentStep de 4)'),
        backgroundColor: const Color(0xFF1E293B),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: widget.onCancel,
        ),
      ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                padding: EdgeInsets.only(
                  top: 24.0,
                  left: 24.0,
                  right: 24.0,
                  bottom: MediaQuery.of(context).padding.bottom + 48.0,
                ),
                child: _buildStepContent(),
              ),
      ),
    );
  }

  Widget _buildStepContent() {
    switch (_currentStep) {
      case 1:
        return _buildPlataformaGuiada(
          title: 'Prestação de Contas — Uber',
          subtitle: 'Minimize o app para tirar o print do extrato e gravar o vídeo do histórico Uber. A IA extrairá os faturamentos automaticamente.',
          platformColor: Colors.black,
          textColor: Colors.white,
          faturamentoIa: _faturamentoLocal?['uber'] ?? widget.jornada['faturamento']?['uber'] ?? 0.0,
          corridasIa: widget.jornada['faturamento']?['corridas_uber'] ?? 0,
          onNaoRodei: () {
            setState(() {
              _currentStep = 2;
            });
          },
          onNext: () {
            setState(() {
              _currentStep = 2;
            });
          },
        );
      case 2:
        return _buildPlataformaGuiada(
          title: 'Prestação de Contas — 99',
          subtitle: 'Minimize o app para tirar o print do extrato e gravar o vídeo do histórico 99. A IA extrairá os faturamentos automaticamente.',
          platformColor: const Color(0xFFFFCC00),
          textColor: Colors.black,
          faturamentoIa: _faturamentoLocal?['noventa_nove'] ?? widget.jornada['faturamento']?['noventa_nove'] ?? 0.0,
          corridasIa: widget.jornada['faturamento']?['corridas_99'] ?? 0,
          onNaoRodei: () {
            setState(() {
              _currentStep = 3;
            });
          },
          onNext: () {
            setState(() {
              _currentStep = 3;
            });
          },
          onBack: () {
            setState(() {
              _currentStep = 1;
            });
          },
        );
      case 3:
        return _buildCorridasParticularesStep();
      case 4:
        return _buildHodometroFinalView();
      default:
        return _buildHodometroFinalView();
    }
  }

  Widget _buildCorridasParticularesStep() {
    final double fatPart = ((_faturamentoLocal?['outros'] ?? widget.jornada['faturamento']?['outros']) as num?)?.toDouble() ?? 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          color: const Color(0xFF1E293B),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.directions_car_rounded, color: Color(0xFF38BDF8), size: 28),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Corridas Particulares (Fora de App)',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                const Text(
                  'Confira o faturamento total em corridas particulares registradas durante a sua jornada.',
                  style: TextStyle(color: Colors.grey, fontSize: 13, height: 1.4),
                ),
                const SizedBox(height: 20),
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F172A),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF334155)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Faturamento Particular:',
                        style: TextStyle(color: Colors.grey, fontSize: 14),
                      ),
                      Text(
                        'R\$ ${fatPart.toStringAsFixed(2)}',
                        style: const TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold, fontSize: 20),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  side: const BorderSide(color: Colors.grey),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () {
                  setState(() {
                    _currentStep = 2;
                  });
                },
                child: const Text('VOLTAR (99)', style: TextStyle(color: Colors.white)),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () {
                  setState(() {
                    _currentStep = 4;
                  });
                },
                child: const Text(
                  'PROSSEGUIR PARA FECHAMENTO',
                  style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 12),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildPlataformaGuiada({
    required String title,
    required String subtitle,
    required Color platformColor,
    Color textColor = Colors.white,
    required dynamic faturamentoIa,
    required dynamic corridasIa,
    required VoidCallback onNaoRodei,
    required VoidCallback onNext,
    VoidCallback? onBack,
  }) {
    final double fatVal = (faturamentoIa is num) ? faturamentoIa.toDouble() : 0.0;
    final int corrVal = (corridasIa is num) ? corridasIa.toInt() : 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          color: const Color(0xFF1E293B),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              children: [
                Text(
                  title,
                  style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(
                  subtitle,
                  style: const TextStyle(color: Colors.grey, fontSize: 13),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),

        // CARD RESULTADO DA IA
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: fatVal > 0 ? Colors.greenAccent : Colors.white12),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Faturamento Detectado por IA', style: TextStyle(color: Colors.grey, fontSize: 12, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text(
                    'R\$ ${fatVal.toStringAsFixed(2).replaceAll('.', ',')}',
                    style: const TextStyle(color: Colors.greenAccent, fontSize: 26, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text('Corridas Lidas', style: TextStyle(color: Colors.grey, fontSize: 12, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  Text(
                    '$corrVal corridas',
                    style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),

        // BANNER INFORMATIVO
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF38BDF8).withOpacity(0.3)),
          ),
          child: Row(
            children: const [
              Icon(Icons.info_outline_rounded, color: Color(0xFF38BDF8), size: 20),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Grave o extrato da plataforma (ex: 99/Uber) usando o gravador de tela do seu celular e selecione o vídeo abaixo.',
                  style: TextStyle(color: Colors.grey, fontSize: 12),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        if (_terminalLogs.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF020617),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF10B981), width: 1.5),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF10B981).withOpacity(0.2),
                  blurRadius: 10,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text('🔴 🟡 🟢', style: TextStyle(fontSize: 10)),
                    const SizedBox(width: 8),
                    const Text(
                      'terminal@gemini-3.6-flash:~',
                      style: TextStyle(color: Color(0xFF38BDF8), fontFamily: 'monospace', fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                    const Spacer(),
                    if (_isAiProcessing)
                      const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF10B981)),
                      ),
                  ],
                ),
                const Divider(color: Colors.white12, height: 16),
                ..._terminalLogs.map((log) {
                  final bool isErr = log.contains('[ERR]');
                  final bool isOk = log.contains('[OK]');
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2.0),
                    child: Text(
                      log,
                      style: TextStyle(
                        color: isErr ? Colors.redAccent : (isOk ? const Color(0xFF10B981) : const Color(0xFF34D399)),
                        fontFamily: 'monospace',                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  );
                }),
                if (_isAiProcessing)
                  const Padding(
                    padding: EdgeInsets.only(top: 4.0),
                    child: Text(' > _ █', style: TextStyle(color: Color(0xFF10B981), fontFamily: 'monospace', fontWeight: FontWeight.bold)),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],

        if (_recordedVideoPath != null && _recordedVideoPath!.isNotEmpty) ...[
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF38BDF8), width: 1.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: const [
                    Icon(Icons.check_circle_rounded, color: Color(0xFF10B981), size: 24),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Vídeo de Extrato Gravado!',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                const Text(
                  'A gravação do seu extrato foi concluída. Clique em ENVIAR PARA IA para processar ou REFAZER para regravar:',
                  style: TextStyle(color: Colors.white70, fontSize: 13),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    // BOTAO 1: ENVIAR PARA IA
                    Expanded(
                      child: ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF10B981),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        onPressed: () async {
                          final res = await Navigator.push<Map<String, dynamic>>(
                            context,
                            MaterialPageRoute(
                              builder: (context) => AiTerminalConsoleScreen(videoPath: _recordedVideoPath!),
                            ),
                          );
                          if (mounted && res != null) {
                            const channel = MethodChannel('com.srclauss.appjornada/overlay');
                            try {
                              await channel.invokeMethod('clearLastRecordedVideo');
                            } catch (_) {}
                            setState(() {
                              _recordedVideoPath = null;
                              _faturamentoLocal = res['faturamento'] ?? res;
                              if (_currentStep == 1) {
                                _currentStep = 2;
                              } else if (_currentStep == 2) {
                                _currentStep = 3;
                              }
                            });
                            await _rodarAuditoria();
                          }
                        },
                        icon: const Icon(Icons.send_rounded, size: 18),
                        label: const Text('ENVIAR PARA IA', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                      ),
                    ),
                    const SizedBox(width: 8),
                    // BOTAO 2: REFAZER GRAVACAO
                    Expanded(
                      child: OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.amber,
                          side: const BorderSide(color: Colors.amber),
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        onPressed: () async {
                          const channel = MethodChannel('com.srclauss.appjornada/overlay');
                          await channel.invokeMethod('clearLastRecordedVideo');
                          setState(() {
                            _recordedVideoPath = null;
                            _terminalLogs.clear();
                          });
                          try {
                            final bool? ok = await channel.invokeMethod<bool>('startNativeVideoRecorder');
                            if (ok == true) {
                              setState(() => _isRecording = true);
                            }
                          } catch (e) {
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('Erro ao reiniciar gravação: $e'), backgroundColor: Colors.red),
                              );
                            }
                          }
                        },
                        icon: const Icon(Icons.refresh_rounded, size: 18),
                        label: const Text('REFAZER', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ] else ...[
          // BOTÃO 1: GRAVAR VÍDEO DA TELA (NATIVO E COMPATÍVEL COM ANDROID 14)
          SizedBox(
            height: 56,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: _isRecording ? Colors.redAccent : const Color(0xFF38BDF8),
                foregroundColor: _isRecording ? Colors.white : Colors.black,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              onPressed: () async {
                const channel = MethodChannel('com.srclauss.appjornada/overlay');
                if (_isRecording) {
                  // PARAR E RECARREGAR VÍDEO
                  try {
                    final String? videoPath = await channel.invokeMethod<String>('stopNativeVideoRecorder');
                    setState(() {
                      _isRecording = false;
                      _recordedVideoPath = videoPath;
                    });
                  } catch (e) {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Erro ao parar gravação: $e'), backgroundColor: Colors.red),
                      );
                    }
                  }
                } else {
                  // CHAMA O PEDIDO DE PERMISSÃO DE GRAVAÇÃO DIRETO NO ANDROID
                  try {
                    final bool? ok = await channel.invokeMethod<bool>('startNativeVideoRecorder');
                    if (ok == true) {
                      setState(() => _isRecording = true);
                    }
                  } catch (e) {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Erro ao solicitar gravação de tela: $e'), backgroundColor: Colors.red),
                      );
                    }
                  }
                }
              },
              icon: Icon(_isRecording ? Icons.stop_circle_rounded : Icons.fiber_manual_record_rounded),
              label: Text(
                _isRecording ? 'PARAR GRAVAÇÃO DE TELA' : 'GRAVAR VÍDEO DA TELA AGORA',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],

        // BOTÃO 2: SELECIONAR VÍDEO DA GALERIA
        if (!_isRecording)
          SizedBox(
            height: 48,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.white,
                side: const BorderSide(color: Colors.white24),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              onPressed: () async {
                final ImagePicker picker = ImagePicker();
                final XFile? video = await picker.pickVideo(source: ImageSource.gallery);
                if (video != null && mounted) {
                  final res = await Navigator.push<Map<String, dynamic>>(
                    context,
                    MaterialPageRoute(
                      builder: (context) => AiTerminalConsoleScreen(videoPath: video.path),
                    ),
                  );
                  if (mounted && res != null) {
                    setState(() {
                      _faturamentoLocal = res['faturamento'] ?? res;
                      if (_currentStep == 1) {
                        _currentStep = 2;
                      } else if (_currentStep == 2) {
                        _currentStep = 3;
                      }
                    });
                    await _rodarAuditoria();
                  }
                }
              },
              icon: const Icon(Icons.video_library_rounded, size: 20),
              label: const Text('ENVIAR VÍDEO DA GALERIA', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
            ),
          ),
        const SizedBox(height: 12),

        // BOTÃO NÃO RODEI NESTA PLATAFORMA
        SizedBox(
          height: 48,
          child: TextButton.icon(
            style: TextButton.styleFrom(
              foregroundColor: Colors.redAccent,
            ),
            onPressed: onNaoRodei,
            icon: const Icon(Icons.block_rounded, size: 18),
            label: const Text('NÃO RODEI NESTA PLATAFORMA HOJE', style: TextStyle(fontWeight: FontWeight.bold)),
          ),
        ),
        const SizedBox(height: 32),

        Row(
          children: [
            if (onBack != null) ...[
              Expanded(
                child: SizedBox(
                  height: 56,
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white70,
                      side: const BorderSide(color: Colors.white24),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    ),
                    onPressed: onBack,
                    child: const Text('VOLTAR'),
                  ),
                ),
              ),
              const SizedBox(width: 16),
            ],
            Expanded(
              child: SizedBox(
                height: 56,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: platformColor,
                    foregroundColor: textColor,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  onPressed: onNext,
                  child: const Text('AVANÇAR', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                ),
              ),
            ),
          ],
        )
      ],
    );
  }

  Widget _buildHodometroFinalView() {
    final fatObj = _faturamentoLocal ?? widget.jornada['faturamento'] ?? {};
    final double fatUber = ((fatObj['uber'] ?? 0.0) as num).toDouble();
    final double fat99 = ((fatObj['noventa_nove'] ?? fatObj['ninety_nine'] ?? 0.0) as num).toDouble();
    final double fatOutros = ((fatObj['outros'] ?? 0.0) as num).toDouble();
    final double fatTotal = fatUber + fat99 + fatOutros;
    final double kmInicial = ((widget.jornada['km']?['inicial'] ?? 0.0) as num).toDouble();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Encerramento & Hodômetro Final',
          style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        const Text(
          'Confira os faturamentos acumulados nesta jornada e registre o hodômetro final do veículo para fechar o dia.',
          style: TextStyle(color: Colors.grey, fontSize: 13),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 20),

        // CARD RESUMO FATURAMENTO DA JORNADA ATUAL
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF10B981)),
          ),
          child: Column(
            children: [
              const Text('Faturamento Total da Jornada Atual', style: TextStyle(color: Colors.grey, fontSize: 13, fontWeight: FontWeight.bold)),
              const SizedBox(height: 6),
              Text(
                'R\$ ${fatTotal.toStringAsFixed(2).replaceAll('.', ',')}',
                style: const TextStyle(color: Color(0xFF10B981), fontSize: 32, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  Text('Uber: R\$ ${fatUber.toStringAsFixed(2).replaceAll('.', ',')}', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
                  Text('99: R\$ ${fat99.toStringAsFixed(2).replaceAll('.', ',')}', style: const TextStyle(color: Color(0xFFFFCC00), fontSize: 13, fontWeight: FontWeight.bold)),
                  Text('Particular: R\$ ${fatOutros.toStringAsFixed(2).replaceAll('.', ',')}', style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 13, fontWeight: FontWeight.bold)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // INFORMACAO HODOMETRO INICIAL DA JORNADA ATUAL
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF334155)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Hodômetro Inicial da Jornada Atual:', style: TextStyle(color: Colors.grey, fontSize: 13)),
              Text('${kmInicial.toStringAsFixed(1)} KM', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
            ],
          ),
        ),
        const SizedBox(height: 20),

        // DADOS DO FECHAMENTO HODOMETRO
        const Text(
          'Foto do Hodômetro Final (Leitura Automática IA)',
          style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 48,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _fotoKmFinalUrl != null ? const Color(0xFF10B981) : const Color(0xFF1E293B),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: () => _capturarFotoHodometro(ImageSource.camera),
                  icon: Icon(_fotoKmFinalUrl != null ? Icons.check_circle : Icons.camera_alt, color: Colors.blueAccent, size: 18),
                  label: const Text('CÂMERA (IA)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: SizedBox(
                height: 48,
                child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: const BorderSide(color: Color(0xFF334155)),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: () => _capturarFotoHodometro(ImageSource.gallery),
                  icon: const Icon(Icons.photo_library, color: Color(0xFF38BDF8), size: 18),
                  label: const Text('GALERIA (IA)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _kmFinalCtrl,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: 'KM Final do Hodômetro (Mínimo: ${kmInicial.toStringAsFixed(1)} KM)',
            labelStyle: const TextStyle(color: Colors.grey, fontSize: 13),
            filled: true,
            fillColor: const Color(0xFF1E293B),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            prefixIcon: const Icon(Icons.speed, color: Colors.blueAccent),
          ),
        ),
        const SizedBox(height: 32),
        Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 48,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white70,
                    side: const BorderSide(color: Colors.white24),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: () {
                    setState(() {
                      _currentStep = 3;
                    });
                  },
                  child: const Text('VOLTAR'),
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: SizedBox(
                height: 48,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: _loading ? null : _finalizarJornada,
                  child: _loading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('ENCERRAR JORNADA', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                ),
              ),
            ),
          ],
        )
      ],
    );
  }
}

