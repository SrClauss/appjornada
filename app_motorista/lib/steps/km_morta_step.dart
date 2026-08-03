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
          const SizedBox(height: 32),
          const Text(
            'Ou Aceitar Advertência por Uso Indevido',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 8),
          Card(
            color: const Color(0xFF1E293B),
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'ADVERTÊNCIA DISCIPLINAR - USO INDEVIDO',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.amber),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Por meio deste instrumento, fica formalmente ADVERTIDO(A) que em razão de violação das normas internas de uso indevido do veículo, tendo em vista a utilização para fins particulares sem autorização prévia ontem.',
                    style: TextStyle(fontSize: 12, color: Colors.grey[300]),
                  ),
                  const SizedBox(height: 16),
                  const Text('Assine na tela abaixo:', style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Container(
                    height: 150,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: Colors.black,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.grey[700]!),
                    ),
                    child: GestureDetector(
                      onPanUpdate: (details) {
                        RenderBox renderBox = context.findRenderObject() as RenderBox;
                        setState(() {
                          _points.add(renderBox.globalToLocal(details.globalPosition));
                          _assinado = true;
                          _recusouAssinar = false;
                        });
                      },
                      onPanEnd: (details) => _points.add(null),
                      child: CustomPaint(
                        painter: SignaturePainter(_points),
                      ),
                    ),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(
                        onPressed: () {
                          setState(() {
                            _points.clear();
                            _assinado = false;
                          });
                        },
                        child: const Text('Limpar'),
                      ),
                      TextButton(
                        onPressed: () {
                          setState(() {
                            _points.clear();
                            _assinado = false;
                            _recusouAssinar = true;
                          });
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Registrada a recusa de assinatura.')),
                          );
                        },
                        child: Text(
                          'Recusar Assinatura',
                          style: TextStyle(color: Colors.red[300]),
                        ),
                      ),
                    ],
                  ),
                  if (_recusouAssinar)
                    const Padding(
                      padding: EdgeInsets.only(bottom: 12.0),
                      child: Text(
                        '* O motorista recusou-se a assinar fisicamente. A advertência será gerada no sistema.',
                        style: TextStyle(color: Colors.red, fontSize: 11, fontWeight: FontWeight.bold),
                      ),
                    ),
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF6366F1)),
                      onPressed: _assinarAdvertencia,
                      child: Text(
                        _recusouAssinar ? 'PROSSEGUIR COM RECUSA' : 'PROSSEGUIR COM ASSINATURA',
                        style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                    ),
                  )
                ],
              ),
            ),
          )
        ],
      ),
    );
  }
}
