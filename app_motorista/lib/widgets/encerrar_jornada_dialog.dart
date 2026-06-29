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
  
  bool _loading = false;
  final ImagePicker _picker = ImagePicker();

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
    final km = double.tryParse(_kmController.text) ?? 0;
    if (km <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, digite o KM final.')),
      );
      return;
    }
    if (_fotoHodometroUrl == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, tire foto do hodômetro para encerramento.')),
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
        Navigator.pop(context); // Fechar Dialog
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
    // Escuta mudanças nos controllers para exibir botões de prints dinamicamente
    final showUberPrint = (double.tryParse(_uberController.text) ?? 0.0) > 0;
    final show99Print = (double.tryParse(_noventaNoveController.text) ?? 0.0) > 0;

    return AlertDialog(
      title: const Text('Encerrar Jornada'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Informe o faturamento das plataformas e quilometragem final.'),
            const SizedBox(height: 16),
            TextField(
              controller: _kmController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'KM Final no Hodômetro', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
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
            
            // FOTO HODÔMETRO
            _fotoHodometroUploading
                ? const CircularProgressIndicator()
                : OutlinedButton.icon(
                    onPressed: () => _capturarImagem('km_final', ImageSource.camera, (url) {
                      setState(() {
                        _fotoHodometroUrl = url;
                      });
                    }, (val) {
                      setState(() {
                        _fotoHodometroUploading = val;
                      });
                    }),
                    icon: Icon(
                      _fotoHodometroUrl != null ? Icons.check_circle : Icons.camera_alt,
                      color: _fotoHodometroUrl != null ? Colors.green : Colors.grey,
                    ),
                    label: Text(_fotoHodometroUrl != null ? 'Foto do Hodômetro Salva!' : 'Fotografar Hodômetro Final'),
                  ),
            
            const SizedBox(height: 8),

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
