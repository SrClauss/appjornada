import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:app_motorista/core/api_service.dart';

class EncerrarJornadaDialog extends StatefulWidget {
  final Map<String, dynamic> jornada;
  final VoidCallback onCompleted;

  const EncerrarJornadaDialog({super.key, required this.jornada, required this.onCompleted});

  @override
  State<EncerrarJornadaDialog> createState() => _EncerrarJornadaDialogState();
}

class _EncerrarJornadaDialogState extends State<EncerrarJornadaDialog> {
  final _kmController = TextEditingController();
  final _uberController = TextEditingController();
  final _noventaNoveController = TextEditingController();
  final _outrosController = TextEditingController();
  
  // Imagens do fechamento
  String? _fotoHodometroUrl;
  String? _fotoUberUrl;
  String? _foto99Url;
  
  bool _fotoHodometroUploading = false;
  bool _fotoUberUploading = false;
  bool _foto99Uploading = false;
  double? _kmAiLido;
  
  bool _loading = false;
  final ImagePicker _picker = ImagePicker();

  Future<void> _capturarEProcessarHodometroFinal() async {
    try {
      final XFile? file = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 85,
      );
      if (file != null) {
        setState(() {
          _fotoHodometroUploading = true;
        });
        
        final resOcr = await ApiService.processarFotoOdometro(file.path, contexto: 'km_final');
        
        setState(() {
          _fotoHodometroUploading = false;
          if (resOcr != null && resOcr['foto_url'] != null) {
            _fotoHodometroUrl = resOcr['foto_url'];
            
            if (resOcr['sucesso'] == true && resOcr['km_lido'] != null) {
              final double kmDetectado = (resOcr['km_lido'] as num).toDouble();
              _kmAiLido = kmDetectado;
              if (kmDetectado % 1 == 0) {
                _kmController.text = kmDetectado.toInt().toString();
              } else {
                _kmController.text = kmDetectado.toString();
              }
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  backgroundColor: const Color(0xFF10B981),
                  content: Text('✨ Hodômetro final lido pela IA: ${kmDetectado.toStringAsFixed(1)} km'),
                ),
              );
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  backgroundColor: Colors.orange,
                  content: Text('Foto do hodômetro salva! Confira o KM final informado.'),
                ),
              );
            }
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Falha ao enviar a foto do hodômetro para o servidor.')),
            );
          }
        });
      }
    } catch (e) {
      setState(() {
        _fotoHodometroUploading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao capturar foto: $e')),
      );
    }
  }

  Future<void> _capturarImagem(
    String contexto,
    ImageSource source,
    Function(String) onSuccess,
    Function(bool) onLoadingChange,
  ) async {
    try {
      final XFile? file = await _picker.pickImage(
        source: source,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 80,
      );
      if (file != null) {
        onLoadingChange(true);
        final url = await ApiService.uploadFile(file.path, contexto);
        onLoadingChange(false);
        if (url != null) {
          onSuccess(url);
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Falha ao enviar a imagem para o MinIO.')),
          );
        }
      }
    } catch (e) {
      onLoadingChange(false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao obter imagem: $e')),
      );
    }
  }

  Future<void> _confirmarFechamento() async {
    if (_fotoHodometroUrl == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Colors.red,
          content: Text('É obrigatório tirar a foto do hodômetro final para encerramento.'),
        ),
      );
      return;
    }

    final km = double.tryParse(_kmController.text) ?? 0;
    if (km <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, digite ou confirme o KM final.')),
      );
      return;
    }

    final uberFat = double.tryParse(_uberController.text) ?? 0.0;
    if (uberFat > 0.0 && _fotoUberUrl == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, anexe o print do faturamento da Uber.')),
      );
      return;
    }

    final noventaNoveFat = double.tryParse(_noventaNoveController.text) ?? 0.0;
    if (noventaNoveFat > 0.0 && _foto99Url == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, anexe o print do faturamento da 99.')),
      );
      return;
    }

    setState(() {
      _loading = true;
    });

    try {
      final jId = widget.jornada['_id'] ?? widget.jornada['id'];
      
      var urlStr = '${ApiService.baseUrl}/jornadas/$jId/fechar'
          '?km_final=$km'
          '&faturamento_uber=$uberFat'
          '&faturamento_99=$noventaNoveFat'
          '&faturamento_outros=${double.tryParse(_outrosController.text) ?? 0.0}';
      
      if (_fotoHodometroUrl != null) {
        urlStr += '&foto_km_final_url=$_fotoHodometroUrl';
      }
      if (_fotoUberUrl != null) {
        urlStr += '&comprovante_uber_url=$_fotoUberUrl';
      }
      if (_foto99Url != null) {
        urlStr += '&comprovante_99_url=$_foto99Url';
      }

      final res = await http.patch(
        Uri.parse(urlStr),
        headers: ApiService.headers,
      );

      if (res.statusCode == 200) {
        widget.onCompleted();
        Navigator.pop(context);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erro ao fechar jornada: ${res.body}')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro de conexão: $e')),
      );
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final showUberPrint = (double.tryParse(_uberController.text) ?? 0.0) > 0;
    final show99Print = (double.tryParse(_noventaNoveController.text) ?? 0.0) > 0;

    return AlertDialog(
      title: const Text('Encerrar Jornada'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Fotografe o hodômetro final para leitura automática com IA.'),
            const SizedBox(height: 16),

            // FOTO HODÔMETRO COM IA
            _fotoHodometroUploading
                ? const Center(
                    child: Padding(
                      padding: EdgeInsets.all(12.0),
                      child: Row(
                        children: [
                          CircularProgressIndicator(strokeWidth: 2.5),
                          SizedBox(width: 12),
                          Text('Lendo hodômetro com IA...'),
                        ],
                      ),
                    ),
                  )
                : OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 16),
                      side: BorderSide(
                        color: _fotoHodometroUrl != null ? Colors.green : const Color(0xFF6366F1),
                        width: 1.5,
                      ),
                    ),
                    onPressed: _capturarEProcessarHodometroFinal,
                    icon: Icon(
                      _fotoHodometroUrl != null ? Icons.check_circle : Icons.camera_alt,
                      color: _fotoHodometroUrl != null ? Colors.green : const Color(0xFF6366F1),
                    ),
                    label: Text(
                      _fotoHodometroUrl != null ? 'Refazer Foto do Hodômetro Final' : 'FOTOGRAFAR HODÔMETRO (IA)',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: _fotoHodometroUrl != null ? Colors.green : const Color(0xFF6366F1),
                      ),
                    ),
                  ),

            const SizedBox(height: 12),
            TextField(
              controller: _kmController,
              enabled: _fotoHodometroUrl != null,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: 'KM Final no Hodômetro',
                hintText: _fotoHodometroUrl == null ? 'Tire a foto acima primeiro' : 'Confirme ou ajuste a leitura',
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _uberController,
              keyboardType: TextInputType.number,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(labelText: 'Faturamento Uber (R\$)', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _noventaNoveController,
              keyboardType: TextInputType.number,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(labelText: 'Faturamento 99 (R\$)', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _outrosController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Faturamento Particular (R\$)', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 16),

            // PRINT UBER
            if (showUberPrint) ...[
              _fotoUberUploading
                  ? const CircularProgressIndicator()
                  : OutlinedButton.icon(
                      onPressed: () => _capturarImagem('comprovante', ImageSource.gallery, (url) {
                        setState(() {
                          _fotoUberUrl = url;
                        });
                      }, (val) {
                        setState(() {
                          _fotoUberUploading = val;
                        });
                      }),
                      icon: Icon(
                        _fotoUberUrl != null ? Icons.check_circle : Icons.image,
                        color: _fotoUberUrl != null ? Colors.green : Colors.grey,
                      ),
                      label: Text(_fotoUberUrl != null ? 'Print Uber Anexado!' : 'Anexar Print Uber'),
                    ),
              const SizedBox(height: 8),
            ],

            // PRINT 99
            if (show99Print) ...[
              _foto99Uploading
                  ? const CircularProgressIndicator()
                  : OutlinedButton.icon(
                      onPressed: () => _capturarImagem('comprovante', ImageSource.gallery, (url) {
                        setState(() {
                          _foto99Url = url;
                        });
                      }, (val) {
                        setState(() {
                          _foto99Uploading = val;
                        });
                      }),
                      icon: Icon(
                        _foto99Url != null ? Icons.check_circle : Icons.image,
                        color: _foto99Url != null ? Colors.green : Colors.grey,
                      ),
                      label: Text(_foto99Url != null ? 'Print 99 Anexado!' : 'Anexar Print 99'),
                    ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
        ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
          onPressed: _loading || _fotoHodometroUploading || _fotoUberUploading || _foto99Uploading
              ? null
              : _confirmarFechamento,
          child: _loading ? const CircularProgressIndicator() : const Text('CONCLUIR ENCERRAMENTO', style: TextStyle(color: Colors.white)),
        )
      ],
    );
  }
}
