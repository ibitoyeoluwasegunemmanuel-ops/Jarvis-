import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const JarvisMobileApp());
}

const _ink = Color(0xFF0B1020);
const _panel = Color(0xFF151D32);
const _muted = Color(0xFF9AA8C4);
const _accent = Color(0xFF8B7CFF);

class JarvisMobileApp extends StatelessWidget {
  const JarvisMobileApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'JARVIS',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          brightness: Brightness.dark,
          scaffoldBackgroundColor: _ink,
          colorScheme: ColorScheme.fromSeed(
            seedColor: _accent,
            brightness: Brightness.dark,
            surface: _panel,
          ),
          useMaterial3: true,
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: _panel,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide.none,
            ),
          ),
        ),
        home: const MobileHome(),
      );
}

class MobileHome extends StatefulWidget {
  const MobileHome({super.key});

  @override
  State<MobileHome> createState() => _MobileHomeState();
}

class _MobileHomeState extends State<MobileHome> {
  static const _storage = FlutterSecureStorage();
  final _urlController = TextEditingController();
  int _tab = 0;
  bool _checking = false;
  String _apiUrl = '';
  String _connection = 'Not connected';
  String _detail = 'Connect this phone to your secure JARVIS cloud workspace.';
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final saved = await _storage.read(key: 'jarvis_api_base_url');
      if (!mounted) return;
      setState(() {
        _apiUrl = saved ?? '';
        _urlController.text = _apiUrl;
        if (_apiUrl.isNotEmpty) {
          _detail = 'Server address saved. Check the connection to continue.';
        }
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _connection = 'Secure storage unavailable';
        _detail = 'This build could not access platform secure storage. Use a real Android or iOS device build.';
      });
    }
  }

  Future<void> _saveAndCheck() async {
    final raw = _urlController.text.trim();
    final uri = Uri.tryParse(raw);
    if (uri == null || uri.scheme != 'https' || uri.host.isEmpty) {
      setState(() => _error = 'Enter your secure HTTPS JARVIS server address.');
      return;
    }
    setState(() {
      _checking = true;
      _error = null;
      _connection = 'Checking connection';
      _detail = 'Checking the configured cloud service…';
    });
    try {
      final base = raw.replaceFirst(RegExp(r'/+$'), '');
      final response = await http
          .get(Uri.parse('$base/health'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw Exception('Server returned HTTP ${response.statusCode}.');
      }
      await _storage.write(key: 'jarvis_api_base_url', value: base);
      if (!mounted) return;
      setState(() {
        _apiUrl = base;
        _connection = 'Server reachable';
        _detail = 'The cloud endpoint responded. Secure account sign-in will be enabled when cloud identity is deployed.';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _connection = 'Connection unavailable';
        _detail = 'Could not reach this HTTPS server. Check the address and try again.';
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  Future<void> _disconnect() async {
    await _storage.delete(key: 'jarvis_api_base_url');
    if (!mounted) return;
    setState(() {
      _apiUrl = '';
      _urlController.clear();
      _connection = 'Not connected';
      _detail = 'This device has been disconnected from its saved server address.';
      _error = null;
    });
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      _overview(),
      _workspace(),
      _deviceSettings(),
    ];
    return Scaffold(
      appBar: AppBar(
        backgroundColor: _ink,
        titleSpacing: 20,
        title: const Row(
          children: [
            Icon(Icons.auto_awesome, color: _accent),
            SizedBox(width: 10),
            Text('JARVIS', style: TextStyle(fontWeight: FontWeight.w800, letterSpacing: 2)),
            SizedBox(width: 9),
            Text('MOBILE', style: TextStyle(color: _muted, fontSize: 10, letterSpacing: 1.5)),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 18),
            child: Icon(Icons.circle, size: 9,
                color: _connection == 'Server reachable' ? Colors.greenAccent : Colors.orangeAccent),
          ),
        ],
      ),
      body: SafeArea(child: AnimatedSwitcher(
        duration: const Duration(milliseconds: 180),
        child: pages[_tab],
      )),
      bottomNavigationBar: NavigationBar(
        backgroundColor: _panel,
        selectedIndex: _tab,
        onDestinationSelected: (value) => setState(() => _tab = value),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.grid_view_rounded), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.work_outline), label: 'Workspace'),
          NavigationDestination(icon: Icon(Icons.devices_other), label: 'Devices'),
        ],
      ),
    );
  }

  Widget _overview() => ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
        children: [
          const Text('YOUR AI, ACROSS DEVICES', style: TextStyle(color: _accent, fontSize: 11, letterSpacing: 1.8, fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          const Text('Good to have you\nhere.', style: TextStyle(fontSize: 32, height: 1.12, fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          const Text('Your JARVIS companion for staying connected to your work, projects and systems.', style: TextStyle(color: _muted, height: 1.5)),
          const SizedBox(height: 24),
          _statusCard(),
          const SizedBox(height: 16),
          Row(children: [
            Expanded(child: _metric(Icons.folder_copy_outlined, 'Projects', 'Cloud sync pending')),
            const SizedBox(width: 12),
            Expanded(child: _metric(Icons.notifications_none, 'Alerts', 'Not configured')),
          ]),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: _metric(Icons.mic_none, 'Voice', 'Coming next')),
            const SizedBox(width: 12),
            Expanded(child: _metric(Icons.verified_user_outlined, 'Approvals', 'Secure API pending')),
          ]),
          const SizedBox(height: 22),
          _sectionTitle('WHAT THIS PHONE WILL DO'),
          const SizedBox(height: 12),
          _feature(Icons.chat_bubble_outline, 'Talk to JARVIS', 'Voice and text conversations that follow you between devices.'),
          _feature(Icons.monitor_heart_outlined, 'Monitor your systems', 'Receive service and project alerts even when your PC is off.'),
          _feature(Icons.task_alt, 'Stay on top of work', 'Review projects, tasks and approvals from anywhere.'),
        ],
      );

  Widget _statusCard() => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          gradient: const LinearGradient(colors: [Color(0xFF25254C), Color(0xFF18243A)]),
          border: Border.all(color: _accent.withValues(alpha: .28)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.hub_outlined, color: _accent),
            const SizedBox(width: 9),
            const Expanded(child: Text('CLOUD CONNECTION', style: TextStyle(fontSize: 11, letterSpacing: 1.2, fontWeight: FontWeight.w700))),
            Text(_connection, style: const TextStyle(color: _muted, fontSize: 11)),
          ]),
          const SizedBox(height: 13),
          Text(_detail, style: const TextStyle(color: Colors.white, height: 1.45)),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(_error!, style: const TextStyle(color: Colors.orangeAccent, fontSize: 12)),
          ],
          const SizedBox(height: 14),
          SizedBox(width: double.infinity, child: FilledButton(
            onPressed: () => setState(() => _tab = 2),
            child: const Text('Configure connection'),
          )),
        ]),
      );

  Widget _metric(IconData icon, String title, String value) => Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(color: _panel, borderRadius: BorderRadius.circular(17)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, color: _accent),
          const SizedBox(height: 14),
          Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(color: _muted, fontSize: 11)),
        ]),
      );

  Widget _sectionTitle(String text) => Text(text, style: const TextStyle(color: _muted, fontSize: 11, letterSpacing: 1.5, fontWeight: FontWeight.w700));

  Widget _feature(IconData icon, String title, String subtitle) => Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(padding: const EdgeInsets.all(10), decoration: BoxDecoration(color: _panel, borderRadius: BorderRadius.circular(12)), child: Icon(icon, color: _accent, size: 19)),
          const SizedBox(width: 13),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text(subtitle, style: const TextStyle(color: _muted, height: 1.4, fontSize: 12)),
          ])),
        ]),
      );

  Widget _workspace() => ListView(padding: const EdgeInsets.all(20), children: [
        const Text('WORKSPACE', style: TextStyle(color: _accent, fontSize: 11, letterSpacing: 1.6, fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),
        const Text('Your work, in your pocket.', style: TextStyle(fontSize: 27, fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),
        const Text('Projects, activity, tasks and decisions will appear here after secure cloud sign-in and sync are connected.', style: TextStyle(color: _muted, height: 1.5)),
        const SizedBox(height: 22),
        _feature(Icons.folder_open_outlined, 'Projects', 'Shared project records across Windows and mobile.'),
        _feature(Icons.timeline, 'Activity timeline', 'See what changed, when it changed and where the evidence came from.'),
        _feature(Icons.fact_check_outlined, 'Approvals', 'Review exact actions before authorising them.'),
        _feature(Icons.insights_outlined, 'Monitoring', 'View provider health and acknowledge alerts.'),
        if (_apiUrl.isEmpty) _statusCard(),
      ]);

  Widget _deviceSettings() => ListView(padding: const EdgeInsets.all(20), children: [
        const Text('DEVICE SETUP', style: TextStyle(color: _accent, fontSize: 11, letterSpacing: 1.6, fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),
        const Text('Connect this device', style: TextStyle(fontSize: 27, fontWeight: FontWeight.w700)),
        const SizedBox(height: 9),
        const Text('Enter the HTTPS address of the JARVIS cloud service. This phone must never connect directly to the private Windows loopback gateway.', style: TextStyle(color: _muted, height: 1.5)),
        const SizedBox(height: 20),
        TextField(
          controller: _urlController,
          keyboardType: TextInputType.url,
          autocorrect: false,
          decoration: const InputDecoration(labelText: 'Secure server address', hintText: 'https://your-jarvis-api.example.com'),
        ),
        const SizedBox(height: 12),
        SizedBox(width: double.infinity, child: FilledButton.icon(
          onPressed: _checking ? null : _saveAndCheck,
          icon: _checking ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.link),
          label: Text(_checking ? 'Checking…' : 'Save and test connection'),
        )),
        if (_apiUrl.isNotEmpty) ...[
          const SizedBox(height: 12),
          OutlinedButton.icon(onPressed: _disconnect, icon: const Icon(Icons.link_off), label: const Text('Disconnect this device')),
        ],
        const SizedBox(height: 22),
        _statusCard(),
        const SizedBox(height: 18),
        const Text('Security', style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        const Text('Server address is stored in platform secure storage. Account sign-in, device registration and cloud sync will be enabled after the cloud identity API is implemented.', style: TextStyle(color: _muted, height: 1.5, fontSize: 12)),
      ]);
}
