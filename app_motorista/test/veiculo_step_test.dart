import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_motorista/steps/veiculo_step.dart';

void main() {
  group('VeiculoStep Widget Tests', () {
    testWidgets('Deve carregar e exibir lista de veículos para seleção', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: VeiculoStep(
              onVeiculoSelected: (veiculo) {},
            ),
          ),
        ),
      );

      // Aguarda o término da busca de veículos (API ou mock fallback)
      await tester.pumpAndSettle();

      // Verifica título explicativo
      expect(find.textContaining('Selecione o veículo'), findsOneWidget);

      // Verifica se exibe ao menos um card de veículo (ListView com Cards)
      expect(find.byType(Card), findsWidgets);
    });
  });
}
