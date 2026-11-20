// ignore: deprecated_member_use
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jarvis_mobile/main.dart';

void main() {
  testWidgets('shows secure JARVIS cloud configuration', (tester) async {
    // Exercise the configuration screen directly. JarvisMobileApp performs
    // asynchronous secure-storage initialization, which is a platform plugin
    // and should be covered by an integration test rather than this widget test.
    await tester.pumpWidget(const MaterialApp(home: ConfigPage(
      busy: false,
      onSave: _noopSave,
    )));

    expect(find.text('Connect JARVIS'), findsOneWidget);
    expect(find.text('JARVIS cloud API HTTPS URL'), findsOneWidget);
    expect(find.text('Supabase project HTTPS URL'), findsOneWidget);
    expect(find.text('Supabase publishable / anon public key'), findsOneWidget);
  });
}

Future<void> _noopSave(String api, String supabase, String key) async {}
