import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';
import '../../../core/errors/api_exception.dart';
import '../../../shared/services/upload_service.dart';
import '../../../shared/widgets/app_button.dart';
import '../../../shared/widgets/app_text_field.dart';
import '../../../shared/widgets/foto_picker_widget.dart';
import '../../../shared/widgets/loading_overlay.dart';
import '../services/jornada_service.dart';

class FecharJornadaScreen extends ConsumerStatefulWidget {
  final String jornadaId;
  const FecharJornadaScreen({super.key, required this.jornadaId});

  @override
  ConsumerState<FecharJornadaScreen> createState() =>
      _FecharJornadaScreenState();
}

class _FecharJornadaScreenState extends ConsumerState<FecharJornadaScreen> {
  final _formKey = GlobalKey<FormState>();
  final _kmFinalCtrl = TextEditingController();
  final _uberCtrl = TextEditingController(text: '0');
  final _noventa9Ctrl = TextEditingController(text: '0');
  final _outrosCtrl = TextEditingController(text: '0');
  final _obsCtrl = TextEditingController();

  File? _fotoOdometro;
  bool _isSaving = false;
  String? _error;

  @override
  void dispose() {
    _kmFinalCtrl.dispose();
    _uberCtrl.dispose();
    _noventa9Ctrl.dispose();
    _outrosCtrl.dispose();
    _obsCtrl.dispose();
    super.dispose();
  }

  Future<Position?> _getGps() async {
    try {
      bool ok = await Geolocator.isLocationServiceEnabled();
      if (!ok) return null;
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied ||
          perm == LocationPermission.deniedForever) return null;
      return await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 8),
        ),
      );
    } catch (_) {
      return null;
    }
  }

  Future<void> _confirmarEncerramento() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Encerrar Jornada'),
        content: const Text(
            'Tem certeza que deseja encerrar a jornada? Esta ação não pode ser desfeita.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Encerrar'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await _fechar();
  }

  Future<void> _fechar() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() {
      _isSaving = true;
      _error = null;
    });

    try {
      String? fotoUrl;
      if (_fotoOdometro != null) {
        fotoUrl = await UploadService.uploadFoto(_fotoOdometro!, contexto: 'km_final');
      }

      final position = await _getGps();

      await JornadaService.fecharJornada(
        jornadaId: widget.jornadaId,
        kmFinal: double.parse(_kmFinalCtrl.text.replaceAll(',', '.')),
        faturamentoUber:
            double.tryParse(_uberCtrl.text.replaceAll(',', '.')) ?? 0,
        faturamento99:
            double.tryParse(_noventa9Ctrl.text.replaceAll(',', '.')) ?? 0,
        faturamentoOutros:
            double.tryParse(_outrosCtrl.text.replaceAll(',', '.')) ?? 0,
        fotoKmFinalUrl: fotoUrl,
        lat: position?.latitude,
        lon: position?.longitude,
        observacoes: _obsCtrl.text.trim().isEmpty ? null : _obsCtrl.text.trim(),
      );

      if (mounted) context.go('/home');
    } on ApiException catch (e) {
      setState(() {
        _isSaving = false;
        _error = e.message;
      });
    } catch (e) {
      setState(() {
        _isSaving = false;
        _error = 'Erro ao encerrar jornada.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Encerrar Jornada')),
      body: LoadingOverlay(
        isLoading: _isSaving,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                AppTextField(
                  label: 'KM final',
                  hint: '12750',
                  controller: _kmFinalCtrl,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) {
                      return 'Informe o KM final';
                    }
                    if (double.tryParse(v.replaceAll(',', '.')) == null) {
                      return 'Valor inválido';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                FotoPickerWidget(
                  label: 'Foto do hodômetro (km final)',
                  onImageSelected: (f) => setState(() => _fotoOdometro = f),
                ),
                const SizedBox(height: 16),
                Text('Faturamento',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                AppTextField(
                  label: 'Uber (R\$)',
                  hint: '0.00',
                  controller: _uberCtrl,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  prefixIcon: const Icon(Icons.phone_android),
                ),
                const SizedBox(height: 8),
                AppTextField(
                  label: '99 (R\$)',
                  hint: '0.00',
                  controller: _noventa9Ctrl,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  prefixIcon: const Icon(Icons.local_taxi),
                ),
                const SizedBox(height: 8),
                AppTextField(
                  label: 'Outros (R\$)',
                  hint: '0.00',
                  controller: _outrosCtrl,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  prefixIcon: const Icon(Icons.attach_money),
                ),
                const SizedBox(height: 16),
                AppTextField(
                  label: 'Observações (opcional)',
                  hint: 'Alguma observação sobre a jornada?',
                  controller: _obsCtrl,
                  keyboardType: TextInputType.multiline,
                ),
                const SizedBox(height: 24),
                if (_error != null) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.errorContainer,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      _error!,
                      style: TextStyle(
                          color:
                              Theme.of(context).colorScheme.onErrorContainer),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
                AppButton(
                  label: 'Encerrar Jornada',
                  icon: Icons.stop_rounded,
                  color: Colors.red,
                  onPressed: _confirmarEncerramento,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
