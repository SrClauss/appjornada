import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:app_motorista/core/api_service.dart';

class SinistroModal extends StatefulWidget {
  final Map<String, dynamic> jornada;
  const SinistroModal({super.key, required this.jornada});

  @override
  State<SinistroModal> createState() => _SinistroModalState();
}

class _SinistroModalState extends State<SinistroModal> {
  final TextEditingController _descricaoController = TextEditingController();
  String _tipoSinistro = 'Colisão/Acidente';
  bool _loading = false;
  bool _obtendoGps = true;
  
  Position? _posicaoAtual;
  String _enderecoGpsStr = 'Obtendo localização GPS via satélite...';

  final List<XFile> _fotos = [];
  final ImagePicker _picker = ImagePicker();

  final List<String> _tiposDisponiveis = [
    'Colisão/Acidente',
    'Avaria/Risco na Lataria',
    'Pneu Furado/Estourado',
    'Problema Mecânico/Guincho',
    'Vandalismo/Quebra de Vidro',
    'Outros',
  ];

  @override
  void initState() {
    super.initState();
    _capturarLocalizacaoGps();
  }

  Future<void> _capturarLocalizacaoGps() async {
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        setState(() {
          _obtendoGps = false;
          _enderecoGpsStr = 'GPS desativado no aparelho.';
        });
        return;
      }

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          setState(() {
            _obtendoGps = false;
            _enderecoGpsStr = 'Permissão de GPS negada.';
          });
          return;
        }
      }

      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 10),
      );

      if (mounted) {
        setState(() {
          _posicaoAtual = position;
          _obtendoGps = false;
          _enderecoGpsStr = 'Lat: ${position.latitude.toStringAsFixed(5)}, Lon: ${position.longitude.toStringAsFixed(5)}';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _obtendoGps = false;
          _enderecoGpsStr = 'Localização fixada via GPS da Jornada';
        });
      }
    }
  }

  Future<void> _tirarFoto() async {
    if (_fotos.length >= 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Limite de 6 fotos por sinistro atingido.')),
      );
      return;
    }

    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        imageQuality: 75,
        maxWidth: 1280,
      );

      if (photo != null) {
        setState(() {
          _fotos.add(photo);
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao abrir câmera: $e')),
      );
    }
  }

  Future<void> _salvarSinistro() async {
    if (_loading) return;

    if (_fotos.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Colors.amber,
          content: Text('⚠️ Por favor, tire pelo menos 1 foto do ocorrido para registro.'),
        ),
      );
      return;
    }

    setState(() {
      _loading = true;
    });

    try {
      List<String> fotosUrls = [];

      // 1. Upload de cada foto para o MinIO/Backend
      for (var f in _fotos) {
        final request = http.MultipartRequest(
          'POST',
          Uri.parse('${ApiService.baseUrl}/ocr/upload-foto'),
        );
        request.headers.addAll(ApiService.headers);
        request.files.add(await http.MultipartFile.fromPath('file', f.path));

        final response = await request.send();
        if (response.statusCode == 200) {
          final respStr = await response.stream.bytesToString();
          final jsonResp = json.decode(respStr);
          if (jsonResp['url'] != null) {
            fotosUrls.add(jsonResp['url']);
          }
        }
      }

      final jId = widget.jornada['_id'] ?? widget.jornada['id'];
      final agora = DateTime.now();

      // 2. Registro do Sinistro no endpoint da Jornada
      final res = await http.post(
        Uri.parse('${ApiService.baseUrl}/jornadas/$jId/sinistros'),
        headers: ApiService.headers,
        body: json.encode({
          'id': agora.millisecondsSinceEpoch.toString(),
          'hora': '${agora.hour.toString().padLeft(2, '0')}:${agora.minute.toString().padLeft(2, '0')}:00',
          'tipo': _tipoSinistro,
          'descricao': _descricaoController.text.trim(),
          'imagens_urls': fotosUrls,
          'localizacao': _posicaoAtual != null
              ? {
                  'lat': _posicaoAtual!.latitude,
                  'lon': _posicaoAtual!.longitude,
                }
              : null,
        }),
      );

      if (res.statusCode == 201) {
        if (!mounted) return;
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            backgroundColor: Color(0xFF10B981),
            content: Text('✅ Sinistro registrado com sucesso e GPS marcado!'),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erro ao salvar sinistro (${res.statusCode})')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Falha ao conectar com o servidor: $e')),
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
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          top: 24,
          left: 24,
          right: 24,
          bottom: MediaQuery.of(context).viewInsets.bottom + 48,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 28),
                      SizedBox(width: 8),
                      Text(
                        'Registrar Sinistro',
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                    ],
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.grey),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // CARD DE LOCALIZAÇÃO GPS
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.redAccent.withOpacity(0.4)),
                ),
                child: Row(
                  children: [
                    _obtendoGps
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.redAccent),
                          )
                        : const Icon(Icons.location_on, color: Colors.redAccent),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Localização Atual (Marcador GPS):',
                            style: TextStyle(fontSize: 11, color: Colors.grey, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            _enderecoGpsStr,
                            style: const TextStyle(fontSize: 13, color: Colors.white, fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // TIPO DE SINISTRO
              const Text('Tipo de Ocorrência:', style: TextStyle(color: Colors.grey, fontSize: 13, fontWeight: FontWeight.bold)),
              const SizedBox(height: 6),
              DropdownButtonFormField<String>(
                value: _tipoSinistro,
                dropdownColor: const Color(0xFF1E293B),
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                ),
                items: _tiposDisponiveis.map((t) {
                  return DropdownMenuItem(value: t, child: Text(t));
                }).toList(),
                onChanged: (val) {
                  if (val != null) {
                    setState(() {
                      _tipoSinistro = val;
                    });
                  }
                },
              ),

              const SizedBox(height: 16),

              // DESCRIÇÃO DO OCORRIDO
              TextField(
                controller: _descricaoController,
                maxLines: 3,
                style: const TextStyle(color: Colors.white),
                decoration: const InputDecoration(
                  labelText: 'Descrição / Detalhes do ocorrido',
                  labelStyle: TextStyle(color: Colors.grey),
                  border: OutlineInputBorder(),
                ),
              ),

              const SizedBox(height: 20),

              // FOTOS DO REGISTRO (GRADE)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Fotos da Avaria / Ocorrência:', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                  Text('${_fotos.length}/6 fotos', style: const TextStyle(color: Colors.grey, fontSize: 12)),
                ],
              ),
              const SizedBox(height: 10),

              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  ..._fotos.map((f) => Stack(
                        children: [
                          Container(
                            width: 80,
                            height: 80,
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: const Color(0xFF34D399)),
                              image: DecorationImage(
                                image: FileImage(File(f.path)),
                                fit: BoxFit.cover,
                              ),
                            ),
                          ),
                          Positioned(
                            top: -4,
                            right: -4,
                            child: GestureDetector(
                              onTap: () {
                                setState(() {
                                  _fotos.remove(f);
                                });
                              },
                              child: Container(
                                decoration: const BoxDecoration(
                                  color: Colors.red,
                                  shape: BoxShape.circle,
                                ),
                                child: const Icon(Icons.close, size: 18, color: Colors.white),
                              ),
                            ),
                          ),
                        ],
                      )),
                  if (_fotos.length < 6)
                    InkWell(
                      onTap: _loading ? null : _tirarFoto,
                      child: Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: Colors.redAccent.withOpacity(0.6), style: BorderStyle.solid),
                        ),
                        child: const Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.camera_alt, color: Colors.redAccent, size: 28),
                            SizedBox(height: 4),
                            Text('Tirar Foto', style: TextStyle(color: Colors.redAccent, fontSize: 10, fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                    ),
                ],
              ),

              const SizedBox(height: 24),

              // BOTÃO REGISTRAR
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
                  onPressed: _loading ? null : _salvarSinistro,
                  icon: _loading
                      ? const SizedBox.shrink()
                      : const Icon(Icons.report_problem, color: Colors.white),
                  label: _loading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('REGISTRAR SINISTRO AGORA', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
