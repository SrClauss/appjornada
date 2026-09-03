import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:app_motorista/core/api_service.dart';

class AuditoriaAnteriorStep extends StatefulWidget {
  final VoidCallback onCompleted;
  const AuditoriaAnteriorStep({super.key, required this.onCompleted});

  @override
  State<AuditoriaAnteriorStep> createState() => _AuditoriaAnteriorStepState();
}

class _AuditoriaAnteriorStepState extends State<AuditoriaAnteriorStep> {
  bool _loading = true;
  bool _hasPendencia = false;
  bool _isPendenteAuditoriaGestor = false;
  Map<String, dynamic>? _jornadaPendenteGestor;
  Map<String, dynamic>? _pendenciaAtual;
  String _justificativa = '';
  String? _midiaUrl;
  bool _uploadingMidia = false;
  final List<Offset?> _points = [];
  bool _assinado = false;
  bool _recusouAssinar = false;

  @override
  void initState() {
    super.initState();
    _checkPendencia();
  }

  Future<void> _checkPendencia() async {
    setState(() {
      _loading = true;
      _isPendenteAuditoriaGestor = false;
      _jornadaPendenteGestor = null;
    });

    // 1. Verifica pendências de KM morta/advertência do motorista
    final pendencias = await ApiService.getPendenciasMotorista();
    if (pendencias.isNotEmpty && pendencias.first is Map) {
      setState(() {
        _hasPendencia = true;
        _pendenciaAtual = Map<String, dynamic>.from(pendencias.first);
        _loading = false;
      });
      return;
    }

    // 2. Verifica se a jornada anterior está encerrada mas com auditoria pendente pelo gestor
    try {
      final res = await http.get(
        Uri.parse('${ApiService.baseUrl}/jornadas/pendente-auditoria'),
        headers: ApiService.headers,
      ).timeout(const Duration(seconds: 4));

      if (res.statusCode == 200) {
        final body = json.decode(res.body);
        if (body is Map && body.isNotEmpty) {
          setState(() {
            _hasPendencia = false;
            _isPendenteAuditoriaGestor = true;
            _jornadaPendenteGestor = Map<String, dynamic>.from(body);
            _loading = false;
          });
          return;
        }
      }
    } catch (e) {
      print('[AuditoriaAnteriorStep] Erro ao checar auditoria pendente do gestor: $e');
    }

    setState(() {
      _hasPendencia = false;
      _pendenciaAtual = null;
      _isPendenteAuditoriaGestor = false;
      _loading = false;
    });
  }

  Future<void> _selecionarEUploadMidia() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 20.0, horizontal: 16.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Selecionar Origem da Mídia',
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            ListTile(
              leading: const Icon(Icons.camera_alt, color: Color(0xFF818CF8)),
              title: const Text('Tirar Foto pela Câmera', style: TextStyle(color: Colors.white)),
              onTap: () => Navigator.pop(ctx, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library, color: Color(0xFF818CF8)),
              title: const Text('Escolher da Galeria de Fotos', style: TextStyle(color: Colors.white)),
              onTap: () => Navigator.pop(ctx, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );

    if (source == null) return;

    try {
      final picker = ImagePicker();
      final XFile? image = await picker.pickImage(
        source: source,
        imageQuality: 80,
      );
      if (image == null) return;

      setState(() {
        _uploadingMidia = true;
      });

      // Faz o upload direto no endpoint /uploads/comprovante do backend
      final url = await ApiService.uploadFile(image.path, 'comprovante');
      if (url != null) {
        setState(() {
          _midiaUrl = url;
          _uploadingMidia = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Mídia enviada ao servidor com sucesso!')),
        );
      } else {
        setState(() {
          _uploadingMidia = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Falha ao enviar arquivo ao servidor.')),
        );
      }
    } catch (e) {
      setState(() {
        _uploadingMidia = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao selecionar mídia: $e')),
      );
    }
  }


  Future<void> _salvarJustificativa() async {
    if (_justificativa.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, descreva o motivo da sua justificativa.')),
      );
      return;
    }
    
    final pendenciaId = _pendenciaAtual?['_id'] ?? _pendenciaAtual?['id'];
    if (pendenciaId != null) {
      final ok = await ApiService.resolverPendenciaMotorista(pendenciaId.toString(), {
        'tipo_resolucao': 'JUSTIFICATIVA',
        'justificativa_texto': _justificativa,
        'foto_justificativa_url': _midiaUrl ?? _justificativa,
      });
      if (ok) {
        widget.onCompleted();
        return;
      }
    }
    widget.onCompleted();
  }

  Future<void> _assinarAdvertencia() async {
    if (!_assinado && !_recusouAssinar) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, assine a advertência ou clique em recusar.')),
      );
      return;
    }

    final pendenciaId = _pendenciaAtual?['_id'] ?? _pendenciaAtual?['id'];
    if (pendenciaId != null) {
      await ApiService.resolverPendenciaMotorista(pendenciaId.toString(), {
        'tipo_resolucao': 'ADVERTENCIA',
        'recusou_assinar': _recusouAssinar,
        'assinatura_url': _recusouAssinar ? null : 'assinatura_digital_app',
      });
    }

    widget.onCompleted();
  }


  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_isPendenteAuditoriaGestor) {
      final dataStr = _jornadaPendenteGestor?['data'] ?? '';
      final veiculoId = _jornadaPendenteGestor?['veiculo_id'] ?? '';
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.amber.withOpacity(0.15),
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.amber.withOpacity(0.5), width: 2),
                ),
                child: const Icon(Icons.pending_actions_rounded, size: 70, color: Colors.amber),
              ),
              const SizedBox(height: 24),
              const Text(
                'Jornada em Auditoria pelo Gestor',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 12),
              Text(
                'Sua jornada do dia $dataStr (Veículo $veiculoId) foi encerrada e está aguardando a auditoria do gestor.',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: Colors.white70, height: 1.4),
              ),
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.amber.withOpacity(0.4)),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.lock_clock, color: Colors.amber, size: 20),
                    SizedBox(width: 8),
                    Text(
                      'STATUS: AUDITORIA PENDENTE',
                      style: TextStyle(color: Colors.amber, fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 36),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366F1),
                  padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: _checkPendencia,
                icon: const Icon(Icons.refresh, color: Colors.white),
                label: const Text(
                  'VERIFICAR AUDITORIA NOVAMENTE',
                  style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
                ),
              ),
            ],
          ),
        ),
      );
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

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(24.0, 24.0, 24.0, 48.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.amber.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.amber.withOpacity(0.4)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.speed_rounded, color: Colors.amber, size: 36),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Pendência de Quilometragem (KM Morta)',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.amber),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _pendenciaAtual?['mensagem'] ??
                          _pendenciaAtual?['descricao'] ??
                          'Identificada diferença de quilometragem na jornada anterior. O registro foi armazenado para acompanhamento da gestão.',
                          style: const TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Opção A: Enviar Justificativa ou Foto',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 8),
            Card(
              color: const Color(0xFF1E293B),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    TextField(
                      maxLines: 2,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: 'Descreva o motivo do deslocamento...',
                        hintStyle: const TextStyle(color: Colors.grey),
                        filled: true,
                        fillColor: const Color(0xFF0F172A),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onChanged: (val) => _justificativa = val,
                    ),
                    const SizedBox(height: 16),
                    OutlinedButton.icon(
                      onPressed: _uploadingMidia ? null : _selecionarEUploadMidia,
                      icon: _uploadingMidia
                          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                          : Icon(_midiaUrl != null ? Icons.check_circle : Icons.attach_file, color: _midiaUrl != null ? Colors.green : const Color(0xFF38BDF8)),
                      label: Text(
                        _midiaUrl != null ? 'Mídia Anexada com Sucesso' : 'ANEXAR FOTO / COMPROVANTE',
                        style: TextStyle(color: _midiaUrl != null ? Colors.green : const Color(0xFF38BDF8), fontWeight: FontWeight.bold),
                      ),
                    ),
                    if (_midiaUrl != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 8.0),
                        child: Text(
                          'Arquivo: ${_midiaUrl!.split('/').last}',
                          style: const TextStyle(color: Colors.greenAccent, fontSize: 11),
                        ),
                      ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF10B981),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        onPressed: _salvarJustificativa,
                        child: const Text('ENVIAR JUSTIFICATIVA', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                      ),
                    )
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Opção B: Assinar Termo de Ciência e Iniciar Jornada',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(height: 8),
            Card(
              color: const Color(0xFF1E293B),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'ASSINATURA DE REGISTRO E LIBERAÇÃO',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Color(0xFF38BDF8)),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Confirmo a ciência sobre a variação de quilometragem da jornada anterior para registro na gestão.',
                      style: TextStyle(fontSize: 12, color: Colors.white70, height: 1.3),
                    ),
                    const SizedBox(height: 16),
                    OutlinedButton.icon(
                      onPressed: () => _abrirModalAssinatura(context),
                      icon: Icon(
                        _assinado ? Icons.check_circle : Icons.draw,
                        color: _assinado ? Colors.green : const Color(0xFF38BDF8),
                      ),
                      label: Text(
                        _assinado ? 'Assinatura Capturada (Alterar)' : 'ABRIR TELA DE ASSINATURA DIGITAL',
                        style: TextStyle(
                          color: _assinado ? Colors.green : const Color(0xFF38BDF8),
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF6366F1),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        onPressed: _assinarAdvertencia,
                        child: const Text(
                          'CONFIRMAR E INICIAR JORNADA',
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  void _abrirModalAssinatura(BuildContext context) {
    showDialog(
      context: context,
      builder: (dialogCtx) {
        final List<Offset?> tempPoints = List.from(_points);
        return StatefulBuilder(
          builder: (stContext, setDialogState) {
            return AlertDialog(
              backgroundColor: const Color(0xFF1E293B),
              title: const Text('Assinatura Digital', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Desenhe sua assinatura dentro do quadro abaixo:', style: TextStyle(color: Colors.grey, fontSize: 13)),
                  const SizedBox(height: 12),
                  Builder(
                    builder: (canvasCtx) {
                      return Container(
                        height: 220,
                        width: double.maxFinite,
                        decoration: BoxDecoration(
                          color: Colors.black,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFF6366F1), width: 1.5),
                        ),
                        child: GestureDetector(
                          onPanStart: (details) {
                            final RenderBox renderBox = canvasCtx.findRenderObject() as RenderBox;
                            final localPos = renderBox.globalToLocal(details.globalPosition);
                            setDialogState(() {
                              tempPoints.add(localPos);
                            });
                          },
                          onPanUpdate: (details) {
                            final RenderBox renderBox = canvasCtx.findRenderObject() as RenderBox;
                            final localPos = renderBox.globalToLocal(details.globalPosition);
                            setDialogState(() {
                              tempPoints.add(localPos);
                            });
                          },
                          onPanEnd: (details) => setDialogState(() => tempPoints.add(null)),
                          child: CustomPaint(
                            painter: SignaturePainter(tempPoints),
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    setDialogState(() {
                      tempPoints.clear();
                    });
                  },
                  child: const Text('Limpar', style: TextStyle(color: Colors.grey)),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(dialogCtx),
                  child: const Text('Cancelar', style: TextStyle(color: Colors.redAccent)),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981)),
                  onPressed: () {
                    setState(() {
                      _points.clear();
                      _points.addAll(tempPoints);
                      _assinado = _points.where((p) => p != null).isNotEmpty;
                      if (_assinado) _recusouAssinar = false;
                    });
                    Navigator.pop(dialogCtx);
                  },
                  child: const Text('SALVAR ASSINATURA', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                ),
              ],
            );
          },
        );
      },
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
