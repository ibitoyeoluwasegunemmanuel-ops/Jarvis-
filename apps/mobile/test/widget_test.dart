import 'package:flutter_test/flutter_test.dart';
import 'package:jarvis_mobile/main.dart';

void main() {
  testWidgets('shows secure JARVIS cloud configuration on first launch', (tester) async {
    await tester.pumpWidget(const JarvisMobileApp());
    await tester.pumpAndSettle();
    expect(find.text('Connect JARVIS'), findsOneWidget);
    expect(find.text('JARVIS cloud API HTTPS URL'), findsOneWidget);
    expect(find.text('Supabase project HTTPS URL'), findsOneWidget);
  });
}
