import 'package:flutter/material.dart';
import 'package:app_motorista/steps/auditoria_anterior_step.dart';

class KmMortaStep extends StatefulWidget {
  final double kmMorta;
  final VoidCallback onCompleted;
  const KmMortaStep({super.key, required this.kmMorta, required this.onCompleted});

  @override
  State<KmMortaStep> createState() => _KmMortaStepState();
}

class _KmMortaStepState extends State<KmMortaStep> {
  bool _documentoAnexado = false;
  final List<Offset?> _points = [];
  bool _assinado = false;
  bool _recusouAssinar = false;

  void _justificarUso() {
    if (!_documentoAnexado) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, anexe a foto da autorização de uso particular.')),
      );
      return;
    }
    widget.onCompleted();
  }

  void _assinarAdvertencia() {
    if (!_assinado && !_recusouAssinar) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, assine a advertência ou clique em recusar.')),
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
              color: const Color(0xFF0EA5E9).withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF0EA5E9).withOpacity(0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.info_outline_rounded, color: Color(0xFF38BDF8), size: 36),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Deslocamento Adicional Registrado',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF38BDF8)),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Diferença de ${widget.kmMorta.toStringAsFixed(1)} KM com relação ao encerramento da jornada anterior deste veículo.',
                        style: const TextStyle(fontSize: 13, color: Colors.white70),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          Card(
            color: const Color(0xFF1E293B),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Registro Informativo de Quilometragem',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'O sistema identificou uma diferença de quilometragem entre a última leitura do veículo e o início desta jornada. Esta informação é registrada no histórico para acompanhamento da gestão.',
                    style: TextStyle(fontSize: 13, color: Colors.grey, height: 1.4),
                  ),
                  const SizedBox(height: 24),
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF10B981),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: widget.onCompleted,
                      child: const Text(
                        'ESTOU CIENTE E CONTINUAR',
                        style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 14),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
