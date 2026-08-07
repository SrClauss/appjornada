import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:app_motorista/core/api_service.dart';
import 'package:app_motorista/core/overlay_service.dart';
import 'package:geolocator/geolocator.dart';
import 'package:ed_screen_recorder/ed_screen_recorder.dart';
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

class _FechamentoWizardScreenState extends State<FechamentoWizardScreen> {
  int _currentStep = 1; // 1: Uber, 2: 99, 3: Outros, 4: Auditoria & Fechamento
  bool _loading = false;
  
  bool _isRecording = false;
  final EdScreenRecorder _screenRecorder = EdScreenRecorder();

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

  @override
  void dispose() {
    _uberValorCtrl.dispose();
    _uberCorridasCtrl.dispose();
    _99ValorCtrl.dispose();
    _99CorridasCtrl.dispose();
    _outrosValorCtrl.dispose();
    _outrosCorridasCtrl.dispose();
    _kmFinalCtrl.dispose();
    super.dispose();
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
          _currentStep = 4;
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

  Future<void> _tirarFotoHodometro() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.camera);
    if (picked == null) return;

    setState(() {
      _loading = true;
    });

    try {
      // Faz upload usando api_service
      final url = await ApiService.uploadFile(picked.path, 'hodometro');
      if (url != null) {
        setState(() {
          _fotoKmFinalUrl = url;
        });
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Foto do hodômetro salva com sucesso!'), backgroundColor: Colors.green),
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
          faturamentoIa: widget.jornada['faturamento']?['uber'] ?? 0.0,
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
          faturamentoIa: widget.jornada['faturamento']?['ninety_nine'] ?? 0.0,
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
        return _buildHodometroFinalView();
      default:
        return const SizedBox();
    }
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

        // BOTÃO GRAVAR VÍDEO
        SizedBox(
          height: 56,
          child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: _isRecording ? Colors.redAccent : const Color(0xFF38BDF8),
              foregroundColor: _isRecording ? Colors.white : Colors.black,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            onPressed: () async {
              if (_isRecording) {
                // Para a gravação e envia o vídeo
                setState(() => _loading = true);
                try {
                  final stopRes = await _screenRecorder.stopRecord();
                  if (stopRes.file != null) {
                    setState(() {
                      _isRecording = false;
                    });
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Gravação finalizada! Enviando para IA analisar...')),
                      );
                    }
                    final res = await ApiService.processarVideoExtrato(stopRes.file!.path);
                    if (mounted) {
                      if (res != null) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Vídeo processado com sucesso!'), backgroundColor: Colors.green),
                        );
                        await _rodarAuditoria(); // Atualiza a tela se necessário
                      } else {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Erro ao processar o vídeo na IA.'), backgroundColor: Colors.red),
                        );
                      }
                    }
                  }
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Erro ao parar gravação: $e'), backgroundColor: Colors.red),
                    );
                  }
                } finally {
                  setState(() => _loading = false);
                }
              } else {
                // Pede permissão e inicia a gravação
                final statusStorage = await Permission.storage.request();
                
                final dir = await getTemporaryDirectory();
                final size = MediaQuery.of(context).size;
                
                try {
                  await _screenRecorder.startRecordScreen(
                    fileName: 'extrato_${DateTime.now().millisecondsSinceEpoch}',
                    audioEnable: false, // Sem áudio, apenas imagens!
                    width: size.width.toInt(),
                    height: size.height.toInt(),
                    dirPathToSave: dir.path,
                  );
                  setState(() {
                    _isRecording = true;
                  });
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Gravação iniciada! Minimize e abra o app do extrato.'), backgroundColor: Colors.green),
                    );
                  }
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Erro ao iniciar gravação: $e'), backgroundColor: Colors.red),
                    );
                  }
                }
              }
            },
            icon: Icon(_isRecording ? Icons.stop_circle_rounded : Icons.fiber_manual_record_rounded),
            label: Text(
              _isRecording ? 'PARAR E ENVIAR VÍDEO' : 'GRAVAR VÍDEO DA TELA', 
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)
            ),
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
    final double fatUber = ((widget.jornada['faturamento']?['uber'] ?? 0.0) as num).toDouble();
    final double fat99 = ((widget.jornada['faturamento']?['ninety_nine'] ?? 0.0) as num).toDouble();
    final double fatTotal = fatUber + fat99;

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
          'Confira os faturamentos extraídos pela IA e fotografe o hodômetro do veículo para finalizar o dia.',
          style: TextStyle(color: Colors.grey, fontSize: 13),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),

        // CARD RESUMO FATURAMENTO IA
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.greenAccent),
          ),
          child: Column(
            children: [
              const Text('Faturamento Total Extraído por IA', style: TextStyle(color: Colors.grey, fontSize: 13, fontWeight: FontWeight.bold)),
              const SizedBox(height: 6),
              Text(
                'R\$ ${fatTotal.toStringAsFixed(2).replaceAll('.', ',')}',
                style: const TextStyle(color: Colors.greenAccent, fontSize: 32, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  Text('Uber: R\$ ${fatUber.toStringAsFixed(2).replaceAll('.', ',')}', style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold)),
                  Text('99: R\$ ${fat99.toStringAsFixed(2).replaceAll('.', ',')}', style: const TextStyle(color: Color(0xFFFFCC00), fontSize: 14, fontWeight: FontWeight.bold)),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),

        // DADOS DO FECHAMENTO HODOMETRO
        const Text(
          'Hodômetro Final do Veículo (Foto Obrigatória)',
          style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 56,
          child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: _fotoKmFinalUrl != null ? Colors.green : const Color(0xFF1E293B),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            onPressed: _tirarFotoHodometro,
            icon: Icon(_fotoKmFinalUrl != null ? Icons.check_circle : Icons.camera_alt, color: _fotoKmFinalUrl != null ? Colors.white : Colors.blueAccent),
            label: Text(_fotoKmFinalUrl != null ? 'FOTO DO HODÔMETRO SALVA ✓' : 'FOTOGRAFAR HODÔMETRO (CÂMERA)'),
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _kmFinalCtrl,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: 'KM Final do Hodômetro',
            labelStyle: const TextStyle(color: Colors.grey),
            filled: true,
            fillColor: const Color(0xFF1E293B),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
            prefixIcon: const Icon(Icons.speed, color: Colors.blueAccent),
          ),
        ),
        const SizedBox(height: 40),
        Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 56,
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white70,
                    side: const BorderSide(color: Colors.white24),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  onPressed: () {
                    setState(() {
                      _currentStep = 2;
                    });
                  },
                  child: const Text('VOLTAR'),
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: SizedBox(
                height: 56,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  onPressed: _loading ? null : _finalizarJornada,
                  child: _loading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('ENCERRAR JORNADA', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
                ),
              ),
            ),
          ],
        )
      ],
    );
  }
}

