import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jarvis_mobile/main.dart';

void main() {
  testWidgets('shows secure JARVIS cloud configuration', (tester) async {
    // ConfigPage is a screen, so provide the MaterialApp environment used by
    // the real mobile application (Directionality, theme and navigation).
    await tester.pumpWidget(MaterialApp(
      home: ConfigPage(
        busy: false,
        onSave: (api, supabase, key) async {},
      ),
    ));

    expect(find.text('Connect JARVIS'), findsOneWidget);
    expect(find.text('JARVIS cloud API HTTPS URL'), findsOneWidget);
    expect(find.text('Supabase project HTTPS URL'), findsOneWidget);
    expect(find.text('Supabase publishable / anon public key'), findsOneWidget);
  });
}
