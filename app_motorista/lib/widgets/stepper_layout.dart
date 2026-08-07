import 'package:flutter/material.dart';

class StepperLayout extends StatelessWidget {
  final String currentStep;
  final Widget child;
  final VoidCallback? onLogout;
  final VoidCallback? onBack;
  const StepperLayout({super.key, required this.currentStep, required this.child, this.onLogout, this.onBack});

  @override
  Widget build(BuildContext context) {
    // Definir índice atual
    final steps = ['auditoria', 'veiculo', 'vistoria', 'km_inicial', 'km_morta'];
    int currentIdx = steps.indexOf(currentStep);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Abertura de Dia (Check-in)'),
        centerTitle: true,
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        leading: onBack != null && currentIdx > 0
            ? IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: onBack,
                tooltip: 'Voltar ao passo anterior',
              )
            : null,
        actions: onLogout != null ? [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: onLogout,
            tooltip: 'Sair / Deslogar',
          )
        ] : null,
      ),
      body: SafeArea(
        child: Column(
          children: [
            // INDICADOR DE PASSO
            Container(
              padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 16),
              color: const Color(0xFF1E293B),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildStepDot(1, 'Auditoria', currentIdx >= 0),
                  _buildLine(currentIdx >= 1),
                  _buildStepDot(2, 'Veículo', currentIdx >= 1),
                  _buildLine(currentIdx >= 2),
                  _buildStepDot(3, 'Vistoria', currentIdx >= 2),
                  _buildLine(currentIdx >= 3),
                  _buildStepDot(4, 'KM & Hodôm.', currentIdx >= 3),
                ],
              ),
            ),
            Expanded(child: child),
          ],
        ),
      ),
    );
  }

  Widget _buildStepDot(int step, String label, bool active) {
    return Column(
      children: [
        Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: active ? const Color(0xFF6366F1) : const Color(0xFF334155),
          ),
          child: Center(
            child: Text(
              step.toString(),
              style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: active ? FontWeight.bold : FontWeight.normal,
            color: active ? Colors.white : Colors.grey,
          ),
        )
      ],
    );
  }

  Widget _buildLine(bool active) {
    return Expanded(
      child: Container(
        height: 3,
        color: active ? const Color(0xFF6366F1) : const Color(0xFF334155),
      ),
    );
  }
}
