import 'package:flutter/material.dart';

class AuditoriaAnteriorStep extends StatefulWidget {
  final VoidCallback onCompleted;
  const AuditoriaAnteriorStep({super.key, required this.onCompleted});

  @override
  State<AuditoriaAnteriorStep> createState() => _AuditoriaAnteriorStepState();
}

class _AuditoriaAnteriorStepState extends State<AuditoriaAnteriorStep> {
  bool _loading = true;
  bool _hasPendencia = false;
  String _justificativa = '';
  final List<Offset?> _points = [];
  bool _assinado = false;
  bool _recusouAssinar = false;

  @override
  void initState() {
    super.initState();
    _checkPendencia();
  }

  Future<void> _checkPendencia() async {
    // Simula auditoria do dia anterior no BD
    await Future.delayed(const Duration(seconds: 1));
    // Sem pendências no primeiro uso / estado limpo
    setState(() {
      _hasPendencia = false;
      _loading = false;
    });
  }

  void _salvarJustificativa() {
    if (_justificativa.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, digite sua justificativa ou envie um atestado.')),
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
    // Envia advertência assinada/recusada e libera
    widget.onCompleted();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (!_hasPendencia) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.check_circle_outline, size: 80, color: Colors.green),
            const SizedBox(height: 24),
            const Text(
              'Tudo Certo!',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text('A jornada do dia anterior foi concluída corretamente.'),
            const SizedBox(height: 40),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366F1),
                padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 16),
              ),
              onPressed: widget.onCompleted,
              child: const Text('PROSSEGUIR', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
            )
          ],
        ),
      );
    }

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
                    children: const [
                      Text(
                        'Jornada Anterior Pendente',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.red),
                      ),
                      Text('Identificamos que você faltou ou não registrou jornada ontem.'),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          const Text(
            'Opção A: Enviar Justificativa / Atestado',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  TextField(
                    maxLines: 2,
                    decoration: const InputDecoration(
                      hintText: 'Explique o motivo da ausência...',
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (val) => _justificativa = val,
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton.icon(
                    onPressed: () {
                      // Simula upload de atestado
                      setState(() {
                        _justificativa = 'Atestado médico anexado em foto.';
                      });
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Atestado médico carregado com sucesso!')),
                      );
                    },
                    icon: const Icon(Icons.camera_alt),
                    label: const Text('Anexar Atestado / Autorização'),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981)),
                      onPressed: _salvarJustificativa,
                      child: const Text('ENVIAR JUSTIFICATIVA', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                    ),
                  )
                ],
              ),
            ),
          ),
          const SizedBox(height: 32),
          const Text(
            'Opção B: Assinar Advertência Disciplinar',
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
                    'ADVERTÊNCIA DISCIPLINAR',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.amber),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Por meio deste instrumento, fica formalmente ADVERTIDO(A) que em razão de sua ausência ao trabalho ontem, sem justificativa, fica sujeito(a) às regras disciplinares da CLT. A ausência não justificada prejudica a equipe. Solicitamos que tal conduta não se repita.',
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

class SignaturePainter extends CustomPainter {
  final List<Offset?> points;
  SignaturePainter(this.points);

  @override
  void paint(Canvas canvas, Size size) {
    Paint paint = Paint()
      ..color = Colors.white
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 3.0;

    for (int i = 0; i < points.length - 1; i++) {
      if (points[i] != null && points[i + 1] != null) {
        canvas.drawLine(points[i]!, points[i + 1]!, paint);
      }
    }
  }

  @override
  bool shouldRepaint(SignaturePainter oldDelegate) => true;
}
