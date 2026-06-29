import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:app_motorista/main.dart';

void main() {
  testWidgets('App starts with splash loading indicator', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const AppJornadaMotorista());

    // Verify that the splash screen shows a CircularProgressIndicator.
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
