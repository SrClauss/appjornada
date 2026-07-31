import 'package:flutter/material.dart';

class KmMortaStep extends StatefulWidget {
  final double kmMorta;
  final VoidCallback onCompleted;
  const KmMortaStep({super.key, required this.kmMorta, required this.onCompleted});

  @override
  State<KmMortaStep> createState() => _KmMortaStepState();
}

class _KmMortaStepState extends State<KmMortaStep> {
  bool _documentoAnexado = false;

  void _justificarUso() {
    if (!_documentoAnexado) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, anexe a foto da autorização de uso particular.')),
      );
      return;
    }
    widget.onCompleted();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.red.withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.red.withOpacity(0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.warning_amber_rounded, color: Colors.red, size: 36),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'KM Morta Detectada!',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.red),
                      ),
                      Text(
                        'Diferença de ${widget.kmMorta.toStringAsFixed(1)} KM com relação ao fim do dia anterior do veículo.',
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          const Text(
            'Justificar Uso Particular do Veículo',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  const Text('Se você utilizou o veículo com autorização prévia, anexe a foto do documento.'),
                  const SizedBox(height: 16),
                  OutlinedButton.icon(
                    onPressed: () {
                      setState(() {
                        _documentoAnexado = true;
                      });
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Autorização de uso particular carregada com sucesso!')),
                      );
                    },
                    icon: const Icon(Icons.camera_alt),
                    label: Text(_documentoAnexado ? 'Autorização Anexada!' : 'Anexar Autorização Visual'),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981)),
                      onPressed: _justificarUso,
                      child: const Text('PROSSEGUIR COM AUTORIZAÇÃO', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                    ),
                  )
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
