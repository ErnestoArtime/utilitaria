// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';

import 'package:utilitaria/main.dart';

void main() {
  testWidgets('muestra el panel principal', (WidgetTester tester) async {
    await tester.pumpWidget(const UtilitariaApp());
    expect(find.text('Panel común'), findsOneWidget);
    expect(find.text('Saldo compartido'), findsOneWidget);
    expect(find.text('Alertas'), findsOneWidget);
  });
}
