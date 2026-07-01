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
  late String _urlComprovante;
  late String _imagePath;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _urlComprovante = widget.revisionData['url_comprovante'] ?? '';
    _imagePath = widget.revisionData['filePath'] ?? '';
  }

  Future<void> _excluir() async {
    setState(() {
      _loading = true;
    });

    try {
      if (_urlComprovante.isNotEmpty) {
        await ApiService.deletarComprovante(_urlComprovante);
      }
      await OverlayService.clearWarning();
      
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Comprovante excluído com sucesso.'),
          backgroundColor: Colors.orange,
        ),
      );
      widget.onCompleted();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Erro ao excluir comprovante: $e'),
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
        title: const Text('Comprovante Não Identificado'),
        backgroundColor: const Color(0xFF1E293B),
        automaticallyImplyLeading: false, // Sem botão de voltar/stack
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Não foi possível identificar os dados deste comprovante.',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              const Text(
                'Para continuar a sua jornada, você deve excluir este print e capturar um novo comprovante legível.',
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 14,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white10),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: InteractiveViewer(
                      panEnabled: true,
                      minScale: 0.5,
                      maxScale: 4.0,
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
                                      const Center(child: Icon(Icons.broken_image, size: 64, color: Colors.white30)),
                                )
                              : const Center(child: Icon(Icons.image, size: 64, color: Colors.white30))),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                height: 54,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.redAccent,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    elevation: 2,
                  ),
                  onPressed: _loading ? null : _excluir,
                  icon: _loading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                        )
                      : const Icon(Icons.delete_forever),
                  label: const Text(
                    'Excluir e Voltar para Jornada',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
