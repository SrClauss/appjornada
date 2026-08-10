import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:app_motorista/core/api_service.dart';

class KmInicialStep extends StatefulWidget {
  final Map<String, dynamic> veiculo;
  final double? initialKm;
  final String? fotoHodometroUrl;
  final Function(double, bool, double, String?) onCompleted;

  const KmInicialStep({
    super.key,
    required this.veiculo,
    this.initialKm,
    this.fotoHodometroUrl,
    required this.onCompleted,
  });

  @override
  State<KmInicialStep> createState() => _KmInicialStepState();
}

class _KmInicialStepState extends State<KmInicialStep> {
  final _kmController = TextEditingController();
  bool _fotoHodometro = false;
  String? _fotoHodometroUrl;
  double? _kmAiLido;
  bool _kmEditadoManualmente = false;

  bool _loading = false;
  String? _errorMessage;
  final ImagePicker _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    if (widget.initialKm != null) {
      if (widget.initialKm! % 1 == 0) {
        _kmController.text = widget.initialKm!.toInt().toString();
      } else {
        _kmController.text = widget.initialKm!.toString();
      }
    }
    _fotoHodometroUrl = widget.fotoHodometroUrl;
    if (_fotoHodometroUrl != null) {
      _fotoHodometro = true;
    }
    _kmController.addListener(_onKmChanged);
  }

  void _onKmChanged() {
    if (_kmAiLido != null) {
      final currentVal = double.tryParse(_kmController.text);
      if (currentVal != null && (currentVal - _kmAiLido!).abs() > 0.001) {
        if (!_kmEditadoManualmente) {
          setState(() {
            _kmEditadoManualmente = true;
          });
        }
      } else if (currentVal != null && (currentVal - _kmAiLido!).abs() <= 0.001) {
        if (_kmEditadoManualmente) {
          setState(() {
            _kmEditadoManualmente = false;
          });
        }
      }
    } else {
      setState(() {});
    }
  }

  @override
  void dispose() {
    _kmController.removeListener(_onKmChanged);
    _kmController.dispose();
    super.dispose();
  }

  Future<void> _takeFotoELeituraIA() async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 85,
      );
      if (photo != null) {
        setState(() {
          _loading = true;
          _errorMessage = null;
        });

        final resOcr = await ApiService.processarFotoOdometro(photo.path, contexto: 'km_inicial');

        setState(() {
          _loading = false;
          if (resOcr != null && resOcr['foto_url'] != null) {
            _fotoHodometro = true;
            _fotoHodometroUrl = resOcr['foto_url'];

            if (resOcr['sucesso'] == true && resOcr['km_lido'] != null) {
              final double kmDetectado = (resOcr['km_lido'] as num).toDouble();
              _kmAiLido = kmDetectado;
              _kmEditadoManualmente = false;

              if (kmDetectado % 1 == 0) {
                _kmController.text = kmDetectado.toInt().toString();
              } else {
                _kmController.text = kmDetectado.toString();
              }

              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  backgroundColor: const Color(0xFF10B981),
                  content: Text('✨ Hodômetro lido com sucesso pela IA: ${kmDetectado.toStringAsFixed(1)} km'),
                ),
              );
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  backgroundColor: Colors.orange,
                  content: Text('Foto salva! Não foi possível identificar o número com precisão. Por favor, confira o valor.'),
                ),
              );
            }
          } else {
            _errorMessage = 'Falha ao enviar a foto do hodômetro para o servidor.';
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
    if (!_fotoHodometro || _fotoHodometroUrl == null) {
      setState(() {
        _errorMessage = 'É obrigatório fotografar o hodômetro do painel para efetuar a leitura por IA e iniciar a jornada.';
      });
      return;
    }

    final kmDigitado = double.tryParse(_kmController.text);
    if (kmDigitado == null || kmDigitado < 0) {
      setState(() {
        _errorMessage = 'Por favor, informe uma quilometragem inicial válida.';
      });
      return;
    }

    final double kmFinalOntem = (widget.veiculo['km_atual'] as num?)?.toDouble() ?? 50000.0;

    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    await Future.delayed(const Duration(milliseconds: 500));

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

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(24.0, 24.0, 24.0, 48.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Leitura Obrigatoria de Hodometro',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 6),
          const Text(
            'Tire a foto do painel para a IA realizar a leitura automatica da quilometragem inicial.',
            style: TextStyle(color: Colors.white70, fontSize: 14),
          ),
          const SizedBox(height: 20),

          // BOTÃO PRINCIPAL DE CAPTURA DE FOTO DA IA
          InkWell(
            onTap: _loading ? null : _takeFotoELeituraIA,
            child: Container(
              height: 140,
              width: double.infinity,
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: _fotoHodometro ? const Color(0xFF10B981) : const Color(0xFF6366F1),
                  width: 2,
                ),
                boxShadow: [
                  BoxShadow(
                    color: (_fotoHodometro ? const Color(0xFF10B981) : const Color(0xFF6366F1)).withOpacity(0.15),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  )
                ],
              ),
              child: Center(
                child: _loading
                    ? const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          CircularProgressIndicator(color: Color(0xFF6366F1)),
                          SizedBox(height: 12),
                          Text('Lendo hodômetro com IA...', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                        ],
                      )
                    : Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            _fotoHodometro ? Icons.check_circle : Icons.center_focus_strong,
                            size: 46,
                            color: _fotoHodometro ? const Color(0xFF10B981) : const Color(0xFF818CF8),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            _fotoHodometro ? 'Foto Registrada! Toque para refazer' : 'FOTOGRAFAR PAINEL (LEITURA IA)',
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: _fotoHodometro ? const Color(0xFF10B981) : Colors.white,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _fotoHodometro ? 'Hodômetro capturado com sucesso' : 'Obrigatório para iniciar a jornada',
                            style: TextStyle(
                              fontSize: 12,
                              color: _fotoHodometro ? Colors.greenAccent : Colors.grey,
                            ),
                          )
                        ],
                      ),
              ),
            ),
          ),
          const SizedBox(height: 24),

          // CAMPO DE KM (AUTOPREENCHIDO PELA IA OU AJUSTADO)
          TextField(
            controller: _kmController,
            enabled: _fotoHodometro && !_loading,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
            decoration: InputDecoration(
              labelText: 'Quilometragem Inicial (KM)',
              hintText: _fotoHodometro ? 'Confirme o valor lido' : 'Tire a foto do painel acima primeiro',
              prefixIcon: const Icon(Icons.speed, color: Color(0xFF818CF8)),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              filled: true,
              fillColor: _fotoHodometro ? const Color(0xFF0F172A) : const Color(0xFF1E293B),
            ),
          ),
          const SizedBox(height: 12),

          // BADGES E ALERTAS INFORMATIVOS
          if (!_fotoHodometro)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.amber.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.amber.withOpacity(0.4)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.warning_amber_rounded, color: Colors.amber, size: 20),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Passo obrigatório: Toque no botão acima para fotografar o painel.',
                      style: TextStyle(color: Colors.amber, fontSize: 13, fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            )
          else if (_kmEditadoManualmente)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.orange.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.orange.withOpacity(0.5)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.edit_note, color: Colors.orange, size: 22),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Leitura da IA ajustada manualmente para $kmDigitado km.\nA foto será mantida para auditoria.',
                      style: const TextStyle(color: Colors.orange, fontSize: 12, fontWeight: FontWeight.w500),
                    ),
                  ),
                ],
              ),
            )
          else if (_kmAiLido != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF10B981).withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF10B981).withOpacity(0.5)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.auto_awesome, color: Color(0xFF10B981), size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Leitura confirmada pela IA: ${_kmAiLido!.toStringAsFixed(1)} km.',
                      style: const TextStyle(color: Color(0xFF10B981), fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),

          if (_errorMessage != null) ...[
            const SizedBox(height: 16),
            Text(
              _errorMessage!,
              style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
            )
          ],
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            height: 52,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: _fotoHodometro ? const Color(0xFF10B981) : Colors.grey.shade800,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: (_loading || !_fotoHodometro) ? null : _submitKm,
              child: _loading
                  ? const CircularProgressIndicator(color: Colors.white)
                  : Text(
                      _fotoHodometro ? 'PROSSEGUIR E INICIAR' : 'TIRAR FOTO DO HODÔMETRO PARA CONTINUAR',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white),
                    ),
            ),
          )
        ],
      ),
    );
  }
}
