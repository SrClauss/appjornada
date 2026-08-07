import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_motorista/steps/auditoria_anterior_step.dart';

void main() {
  group('AuditoriaAnteriorStep Tests', () {
    testWidgets('Deve renderizar os componentes da tela de auditoria', (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: AuditoriaAnteriorStep(
              onCompleted: () {},
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verifica botão de prosseguir ou formulário de pendências
      expect(find.byType(ElevatedButton), findsWidgets);
    });
  });
}
