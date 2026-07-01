import 'dart:io';
import 'package:flutter/material.dart';
import 'package:app_motorista/core/api_service.dart';
import 'package:app_motorista/core/overlay_service.dart';

class RevisaoComprovanteScreen extends StatefulWidget {
  final Map<String, dynamic> revisionData;
  final VoidCallback onCompleted;

  const RevisaoComprovanteScreen({
    super.key,
    required this.revisionData,
    required this.onCompleted,
  });

  @override
  State<RevisaoComprovanteScreen> createState() => _RevisaoComprovanteScreenState();
}

class _RevisaoComprovanteScreenState extends State<RevisaoComprovanteScreen> {
  final _formKey = GlobalKey<FormState>();
  late String _plataforma;
  late double _valor;
  late String _origem;
  late String _destino;
  late String _urlComprovante;
  late String _imagePath;
  
  bool _loading = false;
  final _valorController = TextEditingController();
  final _origemController = TextEditingController();
  final _destinoController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _plataforma = widget.revisionData['plataforma'] ?? 'UBER';
    final valRaw = widget.revisionData['valor'];
    if (valRaw is num) {
      _valor = valRaw.toDouble();
    } else if (valRaw is String) {
      _valor = double.tryParse(valRaw) ?? 0.0;
    } else {
      _valor = 0.0;
    }
    _origem = widget.revisionData['origem'] ?? '';
    _destino = widget.revisionData['destino'] ?? '';
    _urlComprovante = widget.revisionData['url_comprovante'] ?? '';
    _imagePath = widget.revisionData['filePath'] ?? '';

    _valorController.text = _valor > 0.0 ? _valor.toStringAsFixed(2) : '';
    _origemController.text = _origem;
    _destinoController.text = _destino;
  }

  @override
  void dispose() {
    _valorController.dispose();
    _origemController.dispose();
    _destinoController.dispose();
    super.dispose();
  }

  Future<void> _salvar() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _loading = true;
    });

    try {
      final parsedValor = double.tryParse(_valorController.text) ?? 0.0;
      
      final res = await ApiService.revisarComprovante(
        urlComprovante: _urlComprovante.isNotEmpty ? _urlComprovante : _imagePath,
        plataforma: _plataforma,
        valor: parsedValor,
        origem: _origemController.text,
        destino: _destinoController.text,
      );

      if (res != null && res['status'] == 'sucesso') {
        await OverlayService.clearWarning();

        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Dados do comprovante salvos com sucesso!'),
            backgroundColor: Colors.green,
          ),
        );
        widget.onCompleted();
      } else {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Falha ao salvar dados de revisão no servidor.'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Erro: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool fileExists = _imagePath.isNotEmpty && File(_imagePath).existsSync();

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Revisar Comprovante'),
        backgroundColor: const Color(0xFF1E293B),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: widget.onCompleted,
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              flex: 4,
              child: Container(
                margin: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white10),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: fileExists
                      ? Image.file(
                          File(_imagePath),
                          fit: BoxFit.contain,
                        )
                      : (_urlComprovante.isNotEmpty
                          ? Image.network(
                              _urlComprovante,
                              fit: BoxFit.contain,
                              errorBuilder: (context, error, stackTrace) =>
                                  const Center(child: Icon(Icons.broken_image, size: 64)),
                            )
                          : const Center(child: Icon(Icons.image, size: 64))),
                ),
              ),
            ),
            Expanded(
              flex: 5,
              child: Container(
                decoration: const BoxDecoration(
                  color: Color(0xFF1E293B),
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(24),
                    topRight: Radius.circular(24),
                  ),
                ),
                padding: const EdgeInsets.all(24),
                child: Form(
                  key: _formKey,
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          'A IA não conseguiu identificar alguns dados. Por favor, preencha-os manualmente:',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 16),
                        DropdownButtonFormField<String>(
                          value: _plataforma,
                          decoration: const InputDecoration(
                            labelText: 'Plataforma',
                            border: OutlineInputBorder(),
                          ),
                          dropdownColor: const Color(0xFF1E293B),
                          items: const [
                            DropdownMenuItem(value: 'UBER', child: Text('UBER')),
                            DropdownMenuItem(value: '99', child: Text('99')),
                            DropdownMenuItem(value: 'OUTROS', child: Text('OUTROS')),
                          ],
                          onChanged: (val) {
                            if (val != null) {
                              setState(() {
                                _plataforma = val;
                              });
                            }
                          },
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _valorController,
                          keyboardType: const TextInputType.numberWithOptions(decimal: true),
                          decoration: const InputDecoration(
                            labelText: 'Valor Corrida (R\$)',
                            border: OutlineInputBorder(),
                            prefixText: 'R\$ ',
                          ),
                          validator: (val) {
                            if (val == null || val.isEmpty) {
                              return 'Por favor, informe o valor da corrida.';
                            }
                            if (double.tryParse(val) == null) {
                              return 'Informe um valor decimal válido.';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _origemController,
                          decoration: const InputDecoration(
                            labelText: 'Origem (Endereço/Bairro)',
                            border: OutlineInputBorder(),
                          ),
                          validator: (val) {
                            if (val == null || val.isEmpty) {
                              return 'Por favor, informe a origem.';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _destinoController,
                          decoration: const InputDecoration(
                            labelText: 'Destino (Endereço/Bairro)',
                            border: OutlineInputBorder(),
                          ),
                          validator: (val) {
                            if (val == null || val.isEmpty) {
                              return 'Por favor, informe o destino.';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 24),
                        SizedBox(
                          height: 50,
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF6366F1),
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            onPressed: _loading ? null : _salvar,
                            child: _loading
                                ? const CircularProgressIndicator(color: Colors.white)
                                : const Text(
                                    'Salvar e Registrar Faturamento',
                                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                                  ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
