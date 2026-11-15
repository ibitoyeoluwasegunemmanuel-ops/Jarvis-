import 'package:flutter_test/flutter_test.dart';
import 'package:jarvis_mobile/main.dart';

void main() {
  testWidgets('shows secure JARVIS cloud configuration on first launch', (tester) async {
    await tester.pumpWidget(const JarvisMobileApp());

    // The initial progress indicator is intentionally animated, so
    // pumpAndSettle would wait forever. Give secure-storage initialization
    // a bounded turn to complete, then render the resulting page.
    await tester.pump(const Duration(seconds: 1));
    await tester.pump();

    expect(find.text('Connect JARVIS'), findsOneWidget);
    expect(find.text('JARVIS cloud API HTTPS URL'), findsOneWidget);
    expect(find.text('Supabase project HTTPS URL'), findsOneWidget);
  });
}
