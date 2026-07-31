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
            'Enviar Justificativa / Atestado',
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
        ],
      ),
    );
  }
}
