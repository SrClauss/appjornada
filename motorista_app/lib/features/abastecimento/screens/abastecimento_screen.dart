import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/errors/api_exception.dart';
import '../../../features/jornada/services/jornada_service.dart';
import '../../../shared/services/upload_service.dart';
import '../../../shared/widgets/app_button.dart';
import '../../../shared/widgets/app_text_field.dart';
import '../../../shared/widgets/foto_picker_widget.dart';
import '../../../shared/widgets/loading_overlay.dart';

class AbastecimentoScreen extends ConsumerStatefulWidget {
  final String jornadaId;
  final double? kmAtual;

  const AbastecimentoScreen({
    super.key,
    required this.jornadaId,
    this.kmAtual,
  });

  @override
  ConsumerState<AbastecimentoScreen> createState() =>
      _AbastecimentoScreenState();
}

class _AbastecimentoScreenState extends ConsumerState<AbastecimentoScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _kmCtrl;
  final _gasolinaCtrl = TextEditingController(text: '0');
  final _gnvCtrl = TextEditingController(text: '0');
  final _etanolCtrl = TextEditingController(text: '0');

  File? _fotoComprovante;
  bool _isSaving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _kmCtrl = TextEditingController(
        text: widget.kmAtual?.toStringAsFixed(1) ?? '');
  }

  @override
  void dispose() {
    _kmCtrl.dispose();
    _gasolinaCtrl.dispose();
    _gnvCtrl.dispose();
    _etanolCtrl.dispose();
    super.dispose();
  }

  Future<void> _salvar() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    final gasolina =
        double.tryParse(_gasolinaCtrl.text.replaceAll(',', '.')) ?? 0;
    final gnv = double.tryParse(_gnvCtrl.text.replaceAll(',', '.')) ?? 0;
    final etanol = double.tryParse(_etanolCtrl.text.replaceAll(',', '.')) ?? 0;

    if (gasolina == 0 && gnv == 0 && etanol == 0) {
      setState(() => _error = 'Informe o valor de pelo menos um combustível.');
      return;
    }

    setState(() {
      _isSaving = true;
      _error = null;
    });

    try {
      String? fotoUrl;
      if (_fotoComprovante != null) {
        fotoUrl = await UploadService.uploadFoto(_fotoComprovante!);
      }

      await JornadaService.registrarAbastecimento(
        jornadaId: widget.jornadaId,
        km: double.parse(_kmCtrl.text.replaceAll(',', '.')),
        valorGasolina: gasolina,
        valorGnv: gnv,
        valorEtanol: etanol,
        fotoComprovanteUrl: fotoUrl,
      );

      if (mounted) context.pop();
    } on ApiException catch (e) {
      setState(() {
        _isSaving = false;
        _error = e.message;
      });
    } catch (_) {
      setState(() {
        _isSaving = false;
        _error = 'Erro ao registrar abastecimento.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Registrar Abastecimento')),
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
                  label: 'KM atual',
                  hint: '12600',
                  controller: _kmCtrl,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) {
                      return 'Informe o KM atual';
                    }
                    if (double.tryParse(v.replaceAll(',', '.')) == null) {
                      return 'Valor inválido';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                Text('Valores do abastecimento',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                AppTextField(
                  label: 'Gasolina (R\$)',
                  hint: '0.00',
                  controller: _gasolinaCtrl,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  prefixIcon: const Icon(Icons.local_gas_station),
                ),
                const SizedBox(height: 8),
                AppTextField(
                  label: 'GNV (R\$)',
                  hint: '0.00',
                  controller: _gnvCtrl,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  prefixIcon: const Icon(Icons.gas_meter),
                ),
                const SizedBox(height: 8),
                AppTextField(
                  label: 'Etanol (R\$)',
                  hint: '0.00',
                  controller: _etanolCtrl,
                  keyboardType: const TextInputType.numberWithOptions(
                      decimal: true),
                  prefixIcon: const Icon(Icons.eco),
                ),
                const SizedBox(height: 16),
                FotoPickerWidget(
                  label: 'Foto do comprovante (opcional)',
                  onImageSelected: (f) =>
                      setState(() => _fotoComprovante = f),
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
                  label: 'Salvar Abastecimento',
                  icon: Icons.save_rounded,
                  color: Colors.teal,
                  onPressed: _salvar,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
