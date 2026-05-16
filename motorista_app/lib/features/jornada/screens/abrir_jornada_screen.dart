import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import '../../../core/auth/auth_provider.dart';
import '../../../core/errors/api_exception.dart';
import '../../../shared/models/veiculo_model.dart';
import '../../../shared/services/upload_service.dart';
import '../../../shared/widgets/app_button.dart';
import '../../../shared/widgets/app_text_field.dart';
import '../../../shared/widgets/foto_picker_widget.dart';
import '../../../shared/widgets/loading_overlay.dart';
import '../../../shared/widgets/pin_pad.dart';
import '../services/jornada_service.dart';

class AbrirJornadaScreen extends ConsumerStatefulWidget {
  const AbrirJornadaScreen({super.key});

  @override
  ConsumerState<AbrirJornadaScreen> createState() => _AbrirJornadaScreenState();
}

class _AbrirJornadaScreenState extends ConsumerState<AbrirJornadaScreen> {
  final _formKey = GlobalKey<FormState>();
  final _kmCtrl = TextEditingController();

  List<VeiculoModel> _veiculos = [];
  VeiculoModel? _veiculoSelecionado;
  File? _fotoOdometro;
  bool _isLoading = true;
  bool _isSaving = false;
  String? _error;
  String? _pinDigitado;

  @override
  void initState() {
    super.initState();
    _loadVeiculos();
  }

  @override
  void dispose() {
    _kmCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadVeiculos() async {
    try {
      final veiculos = await JornadaService.getVeiculos();
      setState(() {
        _veiculos = veiculos;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Erro ao carregar veículos.';
        _isLoading = false;
      });
    }
  }

  Future<Position?> _getGps() async {
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) return null;
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) return null;
      return await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 10),
        ),
      );
    } catch (_) {
      return null;
    }
  }

  void _onPinCompleted(String pin) {
    setState(() => _pinDigitado = pin);
    _submitForm(pin);
  }

  Future<void> _submitForm(String pin) async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_veiculoSelecionado == null) {
      setState(() => _error = 'Selecione um veículo.');
      return;
    }

    setState(() {
      _isSaving = true;
      _error = null;
    });

    try {
      String? fotoUrl;
      if (_fotoOdometro != null) {
        fotoUrl = await UploadService.uploadFoto(_fotoOdometro!);
      }

      final position = await _getGps();
      final user = ref.read(authProvider).user;

      await JornadaService.abrirJornada(
        motoristaId: user!.id,
        veiculoId: _veiculoSelecionado!.idPlaca,
        kmInicial: double.parse(_kmCtrl.text.replaceAll(',', '.')),
        kmInicialUrl: fotoUrl,
        pin: pin,
        lat: position?.latitude,
        lon: position?.longitude,
      );

      if (mounted) context.go('/home');
    } on ApiException catch (e) {
      setState(() {
        _isSaving = false;
        _error = e.message;
        _pinDigitado = null;
      });
      if (e.statusCode == 409 && mounted) {
        showDialog<void>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Jornada já aberta'),
            content: const Text('Você já tem uma jornada aberta hoje.'),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.pop(context);
                  context.go('/home');
                },
                child: const Text('Ver jornada ativa'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      setState(() {
        _isSaving = false;
        _error = 'Erro ao abrir jornada. Tente novamente.';
        _pinDigitado = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Abrir Jornada')),
      body: LoadingOverlay(
        isLoading: _isSaving,
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Vehicle dropdown
                      DropdownButtonFormField<VeiculoModel>(
                        value: _veiculoSelecionado,
                        decoration: InputDecoration(
                          labelText: 'Veículo',
                          border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12)),
                          contentPadding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 14),
                        ),
                        items: _veiculos
                            .map((v) => DropdownMenuItem(
                                  value: v,
                                  child: Text(v.toString()),
                                ))
                            .toList(),
                        onChanged: (v) =>
                            setState(() => _veiculoSelecionado = v),
                        validator: (_) => _veiculoSelecionado == null
                            ? 'Selecione um veículo'
                            : null,
                      ),
                      const SizedBox(height: 16),

                      // KM inicial
                      AppTextField(
                        label: 'KM inicial',
                        hint: '12500',
                        controller: _kmCtrl,
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                        validator: (v) {
                          if (v == null || v.trim().isEmpty) {
                            return 'Informe o KM inicial';
                          }
                          if (double.tryParse(v.replaceAll(',', '.')) == null) {
                            return 'Valor inválido';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),

                      // Odometer photo
                      FotoPickerWidget(
                        label: 'Foto do hodômetro (km inicial)',
                        onImageSelected: (f) =>
                            setState(() => _fotoOdometro = f),
                      ),
                      const SizedBox(height: 24),

                      // PIN pad
                      Text(
                        'Confirme com seu PIN',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      PinPad(onCompleted: _onPinCompleted),

                      if (_error != null) ...[
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Theme.of(context)
                                .colorScheme
                                .errorContainer,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            _error!,
                            style: TextStyle(
                              color: Theme.of(context)
                                  .colorScheme
                                  .onErrorContainer,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
      ),
    );
  }
}
