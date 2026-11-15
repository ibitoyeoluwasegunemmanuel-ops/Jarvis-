import 'package:flutter_test/flutter_test.dart';
import 'package:jarvis_mobile/main.dart';

void main() {
  testWidgets('shows JARVIS mobile home and navigation', (tester) async {
    await tester.pumpWidget(const JarvisMobileApp());
    await tester.pump();
    expect(find.text('JARVIS'), findsOneWidget);
    expect(find.text('MOBILE'), findsOneWidget);
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Workspace'), findsOneWidget);
    expect(find.text('Devices'), findsOneWidget);
  });
}
