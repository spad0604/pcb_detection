// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';

import 'package:desktop/main.dart';

void main() {
  testWidgets('Dashboard renders key panels', (WidgetTester tester) async {
    await tester.pumpWidget(const PcbInspectorApp());

    expect(find.text('Dataset'), findsOneWidget);
    expect(find.text('Training'), findsOneWidget);
    expect(find.text('Inference'), findsOneWidget);
  });
}
