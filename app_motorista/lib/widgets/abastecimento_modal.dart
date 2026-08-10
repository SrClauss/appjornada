import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:app_motorista/core/api_service.dart';
import 'package:app_motorista/core/gps_service.dart';

import 'package:image_picker/image_picker.dart';

class AbastecimentoModal extends StatefulWidget {
  final Map<String, dynamic> jornada;
  const AbastecimentoModal({super.key, required this.jornada});

  @override
  State<AbastecimentoModal> createState() => _AbastecimentoModalState();
}

class _AbastecimentoModalState extends State<AbastecimentoModal> {
  final _kmController = TextEditingController();
  final _gasolinaController = TextEditingController();
  final _gnvController = TextEditingController();
  final _etanolController = TextEditingController();
  String? _fotoCupomUrl;
  bool _loading = false;
  int _secondsLeft = 1800; // 30 minutos
  late Timer _timer;

  @override
  void initState() {
    super.initState();
    _startTimer();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_secondsLeft > 0) {
        setState(() {
          _secondsLeft--;
        });
      } else {
        _timer.cancel();
        // Pausa por ociosidade excedida
        if (!mounted) return;
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Tempo limite de 30 min excedido! Jornada pausada por ociosidade.')),
        );
      }
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  Future<void> _tirarFotoCupom() async {
    final picker = ImagePicker();
    final img = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (img != null) {
      setState(() {
        _loading = true;
      });
      try {
        final res = await ApiService.processarOcrNotaFiscal(img.path);
        if (res != null && res['sucesso'] == true) {
          setState(() {
            _fotoCupomUrl = res['foto_url'];
            
            // Autopreenchimento com os dados extraidos pela IA Gemini
            final valorTotal = (res['valor_total'] as num?)?.toDouble();
            final tipoCombustivel = '${res['tipo_combustivel']}'.toUpperCase();

            if (valorTotal != null && valorTotal > 0) {
              if (tipoCombustivel.contains('ETANOL')) {
                _etanolController.text = valorTotal.toStringAsFixed(2);
              } else if (tipoCombustivel.contains('GNV')) {
                _gnvController.text = valorTotal.toStringAsFixed(2);
              } else {
                // Padrão: Gasolina/Diesel
                _gasolinaController.text = valorTotal.toStringAsFixed(2);
              }
            }
          });
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                backgroundColor: const Color(0xFF10B981),
                content: Text('✨ Nota fiscal lida com sucesso pela IA! Faturamento de R\$ ${res['valor_total'] ?? 0} preenchido.'),
              ),
            );
          }
        } else {
          // Fallback para upload simples caso a leitura falhe
          final url = await ApiService.uploadFile(img.path, 'abastecimentos');
          setState(() {
            _fotoCupomUrl = url;
          });
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Foto salva! Por favor, confira ou informe os valores.')),
            );
          }
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Erro ao enviar foto: $e')),
          );
        }
      } finally {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _confirmarAbastecimento() async {
    if (_loading) return;
    final km = double.tryParse(_kmController.text) ?? 0;
    if (km < 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, digite o KM atual.')),
      );
      return;
    }
    if (_fotoCupomUrl == null || _fotoCupomUrl!.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, anexe a foto do cupom fiscal.')),
      );
      return;
    }

    setState(() {
      _loading = true;
    });

    try {
      final jId = widget.jornada['_id'] ?? widget.jornada['id'];
      final res = await http.post(
        Uri.parse('${ApiService.baseUrl}/jornadas/$jId/abastecimentos'),
        headers: ApiService.headers,
        body: json.encode({
          'id': DateTime.now().millisecondsSinceEpoch.toString(),
          'km': km,
          'valor_gasolina': double.tryParse(_gasolinaController.text) ?? 0.0,
          'valor_gnv': double.tryParse(_gnvController.text) ?? 0.0,
          'valor_etanol': double.tryParse(_etanolController.text) ?? 0.0,
          'foto_comprovante_url': _fotoCupomUrl,
        }),
      );

      if (res.statusCode == 201) {
        // Reseta o timer de inatividade no rastreamento de background por causa da Nota Fiscal comprovada
        if (_fotoCupomUrl != null && _fotoCupomUrl!.isNotEmpty) {
          GpsService.resetInactivityTimer();
        }

        if (!mounted) return;
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            backgroundColor: Color(0xFF10B981),
            content: Text('✅ Abastecimento registrado e inatividade isentada por Nota Fiscal!'),
          ),
        );
      }
    } catch (_) {} finally {
      setState(() {
        _loading = false;
      });
    }
  }


  @override
  Widget build(BuildContext context) {
    final min = (_secondsLeft ~/ 60).toString().padLeft(2, '0');
    final sec = (_secondsLeft % 60).toString().padLeft(2, '0');

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          top: 24,
          left: 24,
          right: 24,
          bottom: MediaQuery.of(context).viewInsets.bottom + 48,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Registrar Abastecimento',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.red.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red),
                  ),
                  child: Text('Tempo: $min:$sec', style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
                )
              ],
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _kmController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'KM Atual no Hodômetro',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _gasolinaController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Valor Gasolina (R\$)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: _gnvController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Valor GNV (R\$)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _etanolController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Valor Etanol (R\$)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 24),
            InkWell(
              onTap: _loading ? null : _tirarFotoCupom,
              child: Container(
                height: 100,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                      color: (_fotoCupomUrl != null && _fotoCupomUrl!.isNotEmpty)
                          ? Colors.green
                          : Colors.grey[700]!),
                ),
                child: Center(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        (_fotoCupomUrl != null && _fotoCupomUrl!.isNotEmpty)
                            ? Icons.check_circle
                            : Icons.camera_alt,
                        color: (_fotoCupomUrl != null && _fotoCupomUrl!.isNotEmpty)
                            ? Colors.green
                            : Colors.grey,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        (_fotoCupomUrl != null && _fotoCupomUrl!.isNotEmpty)
                            ? 'Cupom anexado com sucesso!'
                            : 'Fotografar Cupom Fiscal (Câmera)',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: (_fotoCupomUrl != null && _fotoCupomUrl!.isNotEmpty)
                              ? Colors.green
                              : Colors.grey,
                        ),
                      )
                    ],
                  ),
                ),
              ),
            ),

            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF6366F1)),
                onPressed: _loading ? null : _confirmarAbastecimento,
                child: _loading
                    ? const CircularProgressIndicator(color: Colors.white)
                    : const Text('SALVAR ABASTECIMENTO', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
}
