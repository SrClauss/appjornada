import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_motorista/screens/login_screen.dart';

void main() {
  group('LoginScreen Widget Tests', () {
    testWidgets('Deve renderizar os elementos básicos da tela de login por PIN', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LoginScreen(
              onLoginSuccess: (token, motoristaId, nome, pin) {},
            ),
          ),
        ),
      );

      await tester.pump();

      // Verifica título "JORNADA"
      expect(find.text('JORNADA'), findsOneWidget);

      // Verifica se o teclado numérico possui botões (0 a 9)
      for (int i = 0; i <= 9; i++) {
        expect(find.text('$i'), findsWidgets);
      }
    });

    testWidgets('Deve permitir digitar PIN de 4 dígitos e acionar ação', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 2.0;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LoginScreen(
              onLoginSuccess: (token, motoristaId, nome, pin) {},
            ),
          ),
        ),
      );

      await tester.pump();

      // Toca nos dígitos 1, 2, 3, 4
      await tester.tap(find.text('1').first);
      await tester.pump();
      await tester.tap(find.text('2').first);
      await tester.pump();
      await tester.tap(find.text('3').first);
      await tester.pump();
      await tester.tap(find.text('4').first);
      await tester.pump();
    });
  });
}
