import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:app_motorista/core/api_service.dart';

class KmInicialStep extends StatefulWidget {
  final Map<String, dynamic> veiculo;
  final Function(double, bool, double, String?) onCompleted;
  const KmInicialStep({super.key, required this.veiculo, required this.onCompleted});

  @override
  State<KmInicialStep> createState() => _KmInicialStepState();
}

class _KmInicialStepState extends State<KmInicialStep> {
  final _kmController = TextEditingController();
  bool _fotoHodometro = false;
  String? _fotoHodometroUrl;
  bool _loading = false;
  String? _errorMessage;
  final ImagePicker _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    final kmAtual = widget.veiculo['km_atual'];
    if (kmAtual != null) {
      if (kmAtual % 1 == 0) {
        _kmController.text = kmAtual.toInt().toString();
      } else {
        _kmController.text = kmAtual.toString();
      }
    }
    _kmController.addListener(_onKmChanged);
  }

  void _onKmChanged() {
    setState(() {});
  }

  @override
  void dispose() {
    _kmController.removeListener(_onKmChanged);
    _kmController.dispose();
    super.dispose();
  }

  Future<void> _takeFoto() async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 80,
      );
      if (photo != null) {
        setState(() {
          _loading = true;
          _errorMessage = null;
        });
        
        final url = await ApiService.uploadFile(photo.path, 'km_inicial');
        
        setState(() {
          _loading = false;
          if (url != null) {
            _fotoHodometro = true;
            _fotoHodometroUrl = url;
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Foto do hodômetro carregada com sucesso!')),
            );
          } else {
            _errorMessage = 'Falha ao enviar a foto para o servidor.';
          }
        });
      }
    } catch (e) {
      setState(() {
        _loading = false;
        _errorMessage = 'Erro ao capturar foto: $e';
      });
    }
  }

  Future<void> _submitKm() async {
    final kmDigitado = double.tryParse(_kmController.text);
    if (kmDigitado == null || kmDigitado <= 0) {
      setState(() {
        _errorMessage = 'Digite um KM Inicial válido';
      });
      return;
    }

    final double kmFinalOntem = widget.veiculo['km_atual'] ?? 50000.0;
    final bool kmAlterado = (kmDigitado - kmFinalOntem).abs() > 0.001;

    if (kmAlterado && (!_fotoHodometro || _fotoHodometroUrl == null)) {
      setState(() {
        _errorMessage = 'O KM foi alterado. É obrigatório tirar foto do hodômetro.';
      });
      return;
    }

    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    // Simula validação de KM Morta
    await Future.delayed(const Duration(seconds: 1));

    double diferenca = kmDigitado - kmFinalOntem;
    bool kmMortaAlert = diferenca > 2.0;

    setState(() {
      _loading = false;
    });

    widget.onCompleted(kmDigitado, kmMortaAlert, diferenca, _fotoHodometroUrl);
  }

  @override
  Widget build(BuildContext context) {
    final kmDigitado = double.tryParse(_kmController.text) ?? 0.0;
    final double kmFinalOntem = (widget.veiculo['km_atual'] as num?)?.toDouble() ?? 50000.0;
    final bool kmAlterado = (kmDigitado - kmFinalOntem).abs() > 0.001;

    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Registro de KM Inicial',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 8),
          const Text('Registre a quilometragem exibida no painel do veículo.'),
          const SizedBox(height: 24),
          TextField(
            controller: _kmController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              labelText: 'Quilometragem Inicial (Hodômetro)',
              prefixIcon: const Icon(Icons.speed),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            kmAlterado
                ? '⚠️ O KM foi alterado em relação ao de ontem ($kmFinalOntem). Foto do painel é obrigatória.'
                : 'ℹ️ O KM informado é igual ao de ontem ($kmFinalOntem). Foto do painel é opcional.',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w500,
              color: kmAlterado ? Colors.amber : Colors.greenAccent,
            ),
          ),
          const SizedBox(height: 24),
          InkWell(
            onTap: _loading ? null : _takeFoto,
            child: Container(
              height: 120,
              width: double.infinity,
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: _fotoHodometro ? const Color(0xFF10B981) : const Color(0xFF475569),
                  width: 1.5,
                ),
              ),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      _fotoHodometro ? Icons.check_circle : Icons.camera_alt,
                      size: 40,
                      color: _fotoHodometro ? const Color(0xFF10B981) : Colors.grey,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _fotoHodometro ? 'Foto capturada!' : 'Fotografar Hodômetro do Painel',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: _fotoHodometro ? const Color(0xFF10B981) : Colors.grey,
                      ),
                    )
                  ],
                ),
              ),
            ),
          ),
          if (_errorMessage != null) ...[
            const SizedBox(height: 16),
            Text(
              _errorMessage!,
              style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
            )
          ],
          const Spacer(),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF6366F1)),
              onPressed: _loading ? null : _submitKm,
              child: _loading
                  ? const CircularProgressIndicator(color: Colors.white)
                  : const Text('PROSSEGUIR E VERIFICAR', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
            ),
          )
        ],
      ),
    );
  }
}
