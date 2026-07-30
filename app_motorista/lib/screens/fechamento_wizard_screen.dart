import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:app_motorista/core/api_service.dart';
import 'package:geolocator/geolocator.dart';

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
                padding: const EdgeInsets.all(24.0),
                child: _buildStepContent(),
              ),
      ),
    );
  }

  Widget _buildStepContent() {
    switch (_currentStep) {
      case 1:
        return _buildFaturamentoForm(
          title: 'Faturamento Uber',
          subtitle: 'Declare as corridas e ganhos na Uber hoje',
          imageAsset: 'assets/uber.png',
          platformColor: Colors.black,
          valorCtrl: _uberValorCtrl,
          corridasCtrl: _uberCorridasCtrl,
          onNext: () {
            setState(() {
              _currentStep = 2;
            });
          },
        );
      case 2:
        return _buildFaturamentoForm(
          title: 'Faturamento 99 Táxi',
          subtitle: 'Declare as corridas e ganhos na 99 hoje',
          imageAsset: 'assets/99.png',
          platformColor: const Color(0xFFFFCC00),
          textColor: Colors.black,
          valorCtrl: _99ValorCtrl,
          corridasCtrl: _99CorridasCtrl,
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
        return _buildFaturamentoForm(
          title: 'Corridas Particulares / Outros',
          subtitle: 'Declare outras corridas fora de plataformas',
          imageAsset: 'assets/outros.png',
          platformColor: Colors.indigo,
          valorCtrl: _outrosValorCtrl,
          corridasCtrl: _outrosCorridasCtrl,
          onNext: _rodarAuditoria,
          onBack: () {
            setState(() {
              _currentStep = 2;
            });
          },
        );
      case 4:
        return _buildAuditoriaView();
      default:
        return const SizedBox();
    }
  }

  Widget _buildFaturamentoForm({
    required String title,
    required String subtitle,
    required String imageAsset,
    required Color platformColor,
    Color textColor = Colors.white,
    required TextEditingController valorCtrl,
    required TextEditingController corridasCtrl,
    required VoidCallback onNext,
    VoidCallback? onBack,
  }) {
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
                  style: TextStyle(color: textColor == Colors.black ? Colors.white : Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Text(
                  subtitle,
                  style: const TextStyle(color: Colors.grey, fontSize: 14),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
        TextField(
          controller: corridasCtrl,
          keyboardType: TextInputType.number,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: 'Quantidade de Corridas',
            labelStyle: const TextStyle(color: Colors.grey),
            filled: true,
            fillColor: const Color(0xFF1E293B),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
            prefixIcon: const Icon(Icons.directions_car, color: Colors.blueAccent),
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: valorCtrl,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: 'Faturamento Total (R\$)',
            labelStyle: const TextStyle(color: Colors.grey),
            filled: true,
            fillColor: const Color(0xFF1E293B),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
            prefixIcon: const Icon(Icons.monetization_on, color: Colors.greenAccent),
          ),
        ),
        const SizedBox(height: 40),
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

  Widget _buildAuditoriaView() {
    if (_auditoriaResult == null) return const SizedBox();
    final comparativo = _auditoriaResult!['comparativo'] as Map<String, dynamic>;
    final podeFechar = _auditoriaResult!['pode_fechar'] as bool;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Relatório de Auditoria de Corridas',
          style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 8),
        const Text(
          'Comparamos suas declarações com os prints processados hoje:',
          style: TextStyle(color: Colors.grey, fontSize: 14),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 24),
        _buildAuditoriaCard('Uber', comparativo['uber'], Colors.black),
        const SizedBox(height: 16),
        _buildAuditoriaCard('99 Táxi', comparativo['noventa_nove'], const Color(0xFFFFCC00)),
        const SizedBox(height: 24),
        
        if (!podeFechar) ...[
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.orange.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.orange),
            ),
            child: const Row(
              children: [
                Icon(Icons.warning, color: Colors.orange),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Divergência detectada! O número de prints processados não bate com o declarado. Por favor, suba os prints restantes.',
                    style: TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
        ],

        // DADOS DO FECHAMENTO HODOMETRO
        const Text(
          'Dados Finais do Veículo',
          style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _kmFinalCtrl,
          keyboardType: TextInputType.number,
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
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: SizedBox(
                height: 56,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF1E293B),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  onPressed: _tirarFotoHodometro,
                  icon: const Icon(Icons.camera_alt, color: Colors.blueAccent),
                  label: Text(_fotoKmFinalUrl != null ? 'FOTO ENVIADA ✓' : 'FOTO HODÔMETRO'),
                ),
              ),
            ),
          ],
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
                height: 56,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: podeFechar ? Colors.green : Colors.redAccent,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  onPressed: _finalizarJornada,
                  child: Text(
                    podeFechar ? 'ENCERRAR JORNADA' : 'FORÇAR ENCERRAMENTO',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white),
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 24),
      ],
    );
  }

  Widget _buildAuditoriaCard(String platformName, Map<String, dynamic> data, Color headerColor) {
    final status = data['status'];
    final declarado = data['declarado'];
    final detectado = data['detectado'];
    final diff = data['diferenca'] as int;

    return Card(
      color: const Color(0xFF1E293B),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      width: 12,
                      height: 12,
                      decoration: BoxDecoration(shape: BoxShape.circle, color: headerColor),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      platformName,
                      style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: status == 'OK' ? Colors.green.withOpacity(0.2) : Colors.red.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    status,
                    style: TextStyle(
                      color: status == 'OK' ? Colors.greenAccent : Colors.redAccent,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                )
              ],
            ),
            const Divider(color: Colors.white10, height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                Column(
                  children: [
                    const Text('Declarado', style: TextStyle(color: Colors.grey, fontSize: 12)),
                    const SizedBox(height: 4),
                    Text('$declarado', style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
                  ],
                ),
                Column(
                  children: [
                    const Text('Lido p/ IA', style: TextStyle(color: Colors.grey, fontSize: 12)),
                    const SizedBox(height: 4),
                    Text('$detectado', style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
                  ],
                ),
              ],
            ),
            if (status != 'OK') ...[
              const Divider(color: Colors.white10, height: 24),
              Text(
                diff < 0 ? 'Faltam ${diff.abs()} comprovantes' : 'Sobraram ${diff.abs()} comprovantes',
                style: const TextStyle(color: Colors.grey, fontSize: 13),
              ),
            ]
          ],
        ),
      ),
    );
  }
}
