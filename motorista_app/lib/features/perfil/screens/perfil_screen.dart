import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/auth/auth_provider.dart';
import '../../../shared/widgets/app_button.dart';
import '../../../shared/widgets/app_text_field.dart';
import '../../../shared/widgets/loading_overlay.dart';
import '../services/perfil_service.dart';

class PerfilScreen extends ConsumerStatefulWidget {
  const PerfilScreen({super.key});

  @override
  ConsumerState<PerfilScreen> createState() => _PerfilScreenState();
}

class _PerfilScreenState extends ConsumerState<PerfilScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _nomeCtrl;
  late final TextEditingController _cpfCtrl;
  late final TextEditingController _telefoneCtrl;

  bool _isSaving = false;
  bool _isEditing = false;
  String? _error;
  String? _success;

  @override
  void initState() {
    super.initState();
    final user = ref.read(authProvider).user;
    _nomeCtrl = TextEditingController(text: user?.nome ?? '');
    _cpfCtrl = TextEditingController(
        text: user?.perfilMotorista?.cpf ?? '');
    _telefoneCtrl = TextEditingController(
        text: user?.perfilMotorista?.telefone ?? '');
  }

  @override
  void dispose() {
    _nomeCtrl.dispose();
    _cpfCtrl.dispose();
    _telefoneCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() {
      _isSaving = true;
      _error = null;
      _success = null;
    });

    try {
      final user = ref.read(authProvider).user!;
      await PerfilService.updatePerfil(
        user.id,
        nome: _nomeCtrl.text.trim(),
        telefone: _telefoneCtrl.text.trim().isEmpty
            ? null
            : _telefoneCtrl.text.trim(),
        cpf: _cpfCtrl.text.trim().isEmpty ? null : _cpfCtrl.text.trim(),
      );
      // Reload user data into auth provider
      await ref.read(authProvider.notifier).loadCurrentUser();
      setState(() {
        _isSaving = false;
        _isEditing = false;
        _success = 'Dados atualizados com sucesso.';
      });
    } catch (e) {
      setState(() {
        _isSaving = false;
        _error = 'Erro ao salvar dados. Tente novamente.';
      });
    }
  }

  Future<void> _logout() async {
    await ref.read(authProvider.notifier).logout();
    if (mounted) context.go('/login');
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).user;
    final perfil = user?.perfilMotorista;
    final cnh = perfil?.cnh;
    final cnhExpired = cnh?.isExpired ?? false;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Meu Perfil'),
        actions: [
          if (!_isEditing)
            IconButton(
              icon: const Icon(Icons.edit),
              tooltip: 'Editar',
              onPressed: () => setState(() {
                _isEditing = true;
                _success = null;
                _error = null;
              }),
            ),
        ],
      ),
      body: LoadingOverlay(
        isLoading: _isSaving,
        child: user == null
            ? const Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // CNH expiry banner
                      if (cnhExpired) ...[
                        Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: Theme.of(context)
                                .colorScheme
                                .errorContainer,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.warning_amber_rounded,
                                  color: Theme.of(context)
                                      .colorScheme
                                      .onErrorContainer),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  'Sua CNH está vencida!\nVencimento: ${cnh!.vencimento}',
                                  style: TextStyle(
                                    color: Theme.of(context)
                                        .colorScheme
                                        .onErrorContainer,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],

                      // Profile avatar + email (read-only)
                      Center(
                        child: CircleAvatar(
                          radius: 40,
                          child: Text(
                            user.nome.isNotEmpty
                                ? user.nome[0].toUpperCase()
                                : '?',
                            style: const TextStyle(fontSize: 32),
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Center(
                        child: Text(
                          user.email,
                          style:
                              Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: Theme.of(context)
                                        .colorScheme
                                        .onSurfaceVariant,
                                  ),
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Editable fields
                      AppTextField(
                        label: 'Nome completo',
                        controller: _nomeCtrl,
                        enabled: _isEditing,
                        validator: (v) => (v == null || v.trim().isEmpty)
                            ? 'Informe o nome'
                            : null,
                      ),
                      const SizedBox(height: 12),
                      AppTextField(
                        label: 'CPF',
                        controller: _cpfCtrl,
                        enabled: _isEditing,
                        keyboardType: TextInputType.number,
                      ),
                      const SizedBox(height: 12),
                      AppTextField(
                        label: 'Telefone',
                        controller: _telefoneCtrl,
                        enabled: _isEditing,
                        keyboardType: TextInputType.phone,
                      ),

                      // CNH section (read-only)
                      if (cnh != null) ...[
                        const SizedBox(height: 20),
                        Text('CNH',
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(
                                    color: Theme.of(context)
                                        .colorScheme
                                        .primary)),
                        const Divider(height: 8),
                        _InfoRow(
                          label: 'Vencimento',
                          value: cnh.vencimento ?? '-',
                          valueColor: cnhExpired
                              ? Theme.of(context).colorScheme.error
                              : null,
                        ),
                      ],

                      // Dados bancários (read-only)
                      if (perfil?.dadosBancarios != null) ...[
                        const SizedBox(height: 20),
                        Text('Dados Bancários',
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(
                                    color: Theme.of(context)
                                        .colorScheme
                                        .primary)),
                        const Divider(height: 8),
                        _InfoRow(
                          label: 'Banco',
                          value: perfil!.dadosBancarios!.banco ?? '-',
                        ),
                        _InfoRow(
                          label: 'Agência',
                          value: perfil.dadosBancarios!.agencia ?? '-',
                        ),
                        _InfoRow(
                          label: 'Conta',
                          value: perfil.dadosBancarios!.conta ?? '-',
                        ),
                        if (perfil.dadosBancarios!.cnpj != null)
                          _InfoRow(
                            label: 'CNPJ',
                            value: perfil.dadosBancarios!.cnpj!,
                          ),
                      ],

                      // Feedback messages
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
                                    .onErrorContainer),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ],
                      if (_success != null) ...[
                        const SizedBox(height: 16),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.green.shade50,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.green),
                          ),
                          child: Text(
                            _success!,
                            style: const TextStyle(color: Colors.green),
                            textAlign: TextAlign.center,
                          ),
                        ),
                      ],

                      const SizedBox(height: 24),

                      // Save / cancel buttons when editing
                      if (_isEditing) ...[
                        AppButton(
                          label: 'Salvar alterações',
                          icon: Icons.save_rounded,
                          onPressed: _save,
                        ),
                        const SizedBox(height: 8),
                        OutlinedButton(
                          onPressed: () {
                            final u = ref.read(authProvider).user;
                            _nomeCtrl.text = u?.nome ?? '';
                            _cpfCtrl.text =
                                u?.perfilMotorista?.cpf ?? '';
                            _telefoneCtrl.text =
                                u?.perfilMotorista?.telefone ?? '';
                            setState(() {
                              _isEditing = false;
                              _error = null;
                            });
                          },
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size.fromHeight(48),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12)),
                          ),
                          child: const Text('Cancelar'),
                        ),
                      ] else ...[
                        // Logout button
                        AppButton(
                          label: 'Sair da conta',
                          icon: Icons.logout_rounded,
                          color: Colors.red,
                          onPressed: _logout,
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

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const _InfoRow({required this.label, required this.value, this.valueColor});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color:
                      Theme.of(context).colorScheme.onSurfaceVariant)),
          Text(value,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600, color: valueColor)),
        ],
      ),
    );
  }
}

