// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:utilitaria/main.dart';

void main() {
  testWidgets('solicita activar un dispositivo sin credenciales',
      (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    await tester.pumpWidget(const UtilitariaApp());
    await tester.pumpAndSettle();
    expect(find.text('Activar este dispositivo'), findsOneWidget);
    expect(find.text('Código de activación'), findsOneWidget);
  });

  testWidgets('muestra el panel principal autenticado',
      (WidgetTester tester) async {
    await tester.pumpWidget(const UtilitariaAppForTesting());
    expect(find.text('Panel común'), findsOneWidget);
    expect(find.text('Saldo compartido'), findsOneWidget);
    expect(find.text('Alertas'), findsOneWidget);
  });
}

class UtilitariaAppForTesting extends StatelessWidget {
  const UtilitariaAppForTesting({super.key});

  @override
  Widget build(BuildContext context) => const MaterialApp(home: AppShell());
}
