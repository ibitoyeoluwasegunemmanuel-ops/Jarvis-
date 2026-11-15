import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'services/jarvis_client.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const JarvisMobileApp());
}

const ink = Color(0xFF0B1020);
const panel = Color(0xFF151D32);
const muted = Color(0xFF9AA8C4);
const accent = Color(0xFF8B7CFF);

class JarvisMobileApp extends StatelessWidget {
  const JarvisMobileApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'JARVIS', debugShowCheckedModeBanner: false,
    theme: ThemeData(
      brightness: Brightness.dark, scaffoldBackgroundColor: ink,
      colorScheme: ColorScheme.fromSeed(seedColor: accent, brightness: Brightness.dark),
      useMaterial3: true,
      inputDecorationTheme: InputDecorationTheme(
        filled: true, fillColor: panel,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
      ),
    ),
    home: const JarvisHome(),
  );
}

class JarvisHome extends StatefulWidget {
  const JarvisHome({super.key});
  @override
  State<JarvisHome> createState() => _JarvisHomeState();
}

class _JarvisHomeState extends State<JarvisHome> {
  final client = JarvisClient();
  static const storage = FlutterSecureStorage();
  bool loading = true, busy = false;
  String? error;
  List<dynamic> workspaces = [], projects = [], alerts = [], devices = [];
  Map<String,dynamic>? workspace, overview;
  int tab = 0;
  String get workspaceId => workspace?['id']?.toString() ?? '';

  @override
  void initState() { super.initState(); init(); }

  Future<void> init() async {
    try {
      await client.load();
      if (client.isConfigured && client.isSignedIn) await loadWorkspaces();
    } catch (e) { error = e.toString(); }
    if (mounted) setState(() => loading = false);
  }

  Future<void> loadWorkspaces({String? selectId}) async {
    workspaces = await client.workspaces();
    if (workspaces.isEmpty) { workspace = null; return; }
    final wanted = selectId ?? workspaceId;
    workspace = workspaces.cast<Map<String,dynamic>>().firstWhere(
      (w) => w['id'].toString() == wanted,
      orElse: () => workspaces.first as Map<String,dynamic>,
    );
    await refreshData();
  }

  Future<void> switchWorkspace(String id) async {
    await loadWorkspaces(selectId: id);
    await ensureDevice();
  }

  Future<void> refreshData() async {
    if (workspaceId.isEmpty) return;
    final id = workspaceId;
    final values = await Future.wait([
      client.overview(id), client.projects(id), client.alerts(id), client.devices(id),
    ]);
    overview = values[0] as Map<String,dynamic>;
    projects = values[1] as List<dynamic>;
    alerts = values[2] as List<dynamic>;
    devices = values[3] as List<dynamic>;
  }

  Future<void> run(Future<void> Function() action) async {
    setState(() { busy = true; error = null; });
    try { await action(); }
    catch (e) { error = e.toString(); }
    if (mounted) setState(() => busy = false);
  }

  Future<void> afterAuth() async {
    await loadWorkspaces();
    if (workspace != null) await ensureDevice();
  }

  Future<void> ensureDevice() async {
    if (workspaceId.isEmpty) return;
    final deviceStorageKey = 'jarvis_registered_device_id_$workspaceId';
    final existing = await storage.read(key: deviceStorageKey);
    if (existing != null && existing.isNotEmpty &&
        devices.any((item) => item['id'].toString() == existing)) return;
    if (existing != null) await storage.delete(key: deviceStorageKey);
    final platform = switch (defaultTargetPlatform) {
      TargetPlatform.android => 'android',
      TargetPlatform.iOS => 'ios',
      _ => 'web',
    };
    final device = await client.registerDevice(
      workspaceId: workspaceId,
      deviceName: platform == 'ios' ? 'iPhone' : platform == 'android' ? 'Android phone' : 'Mobile device',
      platform: platform,
    );
    await storage.write(key: deviceStorageKey, value: device['id'].toString());
    await refreshData();
  }

  Future<void> signOut() async {
    await client.signOut();
    if (workspaceId.isNotEmpty) {
      await storage.delete(key: 'jarvis_registered_device_id_$workspaceId');
    }
    workspaces = []; workspace = null; projects = []; alerts = []; devices = []; overview = null;
  }

  @override
  void dispose() { client.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    if (loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    if (!client.isConfigured) return ConfigPage(
      error: error, busy: busy,
      onSave: (api,supa,key) => run(() async {
        await client.saveConfiguration(apiUrl: api, supabaseUrl: supa, publicKey: key);
        await client.testCloudApi();
        if (mounted) setState(() {});
      }),
    );
    if (!client.isSignedIn) return SignInPage(
      error: error, busy: busy,
      onLogin: (email,password) => run(() async {
        await client.signIn(email,password); await afterAuth(); if (mounted) setState(() {});
      }),
      onSignup: (email,password) => run(() async {
        final signedIn = await client.signUp(email,password);
        if (signedIn) { await afterAuth(); }
        else { error = 'Account created. Confirm your email, then sign in.'; }
        if (mounted) setState(() {});
      }),
    );
    if (workspace == null) return CreateWorkspacePage(
      error: error, busy: busy,
      onCreate: (name) => run(() async {
        await client.createWorkspace(name); await loadWorkspaces(); await ensureDevice();
        if (mounted) setState(() {});
      }),
      onSignOut: () => run(signOut),
    );

    final counts = overview?['counts'] as Map<String,dynamic>? ?? {};
    final pages = [
      ListView(padding: const EdgeInsets.all(20), children: [
        const Text('YOUR AI, ACROSS DEVICES', style: TextStyle(color: accent, letterSpacing: 1.5, fontSize: 11, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        const Text('Good to have you\nhere.', style: TextStyle(fontSize: 32, height: 1.1, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Text(workspace?['name']?.toString() ?? 'JARVIS Workspace', style: const TextStyle(color: muted)),
        const SizedBox(height: 20),
        if (error != null) ErrorLine(error!),
        Row(children: [
          Expanded(child: Metric('Projects', '${counts['projects'] ?? projects.length}', Icons.folder_outlined)),
          const SizedBox(width: 10),
          Expanded(child: Metric('Open alerts', '${counts['open_alerts'] ?? alerts.length}', Icons.notifications_outlined)),
        ]),
        const SizedBox(height: 10),
        Metric('Connected devices', '${counts['active_devices'] ?? devices.length}', Icons.devices),
        const SizedBox(height: 24),
        SectionHeader('RECENT PROJECTS', onRefresh: () => run(refreshData)),
        if (projects.isEmpty) const EmptyLine('No projects have been added to this cloud workspace yet.')
        else ...projects.take(8).map((p) => DataLine(
          title: p['name']?.toString() ?? 'Project',
          subtitle: p['description']?.toString() ?? '',
          trailing: p['status']?.toString(),
          icon: Icons.folder_open,
        )),
        const SizedBox(height: 18),
        const SectionHeader('MONITORING ALERTS'),
        if (alerts.isEmpty) const EmptyLine('No monitoring alerts are recorded for this workspace.')
        else ...alerts.take(8).map((a) => DataLine(
          title: a['title']?.toString() ?? 'Alert',
          subtitle: a['summary']?.toString() ?? '',
          trailing: a['severity']?.toString(),
          icon: Icons.monitor_heart_outlined,
        )),
      ]),
      ListView(padding: const EdgeInsets.all(20), children: [
        const Text('WORKSPACE', style: TextStyle(color: accent, letterSpacing: 1.5, fontSize: 11, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        const Text('Your work, in your pocket.', style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold)),
        const SizedBox(height: 16),
        DropdownButtonFormField<String>(
          value: workspaceId,
          decoration: const InputDecoration(labelText: 'Active workspace'),
          items: workspaces.map((w) => DropdownMenuItem<String>(
            value: w['id'].toString(), child: Text(w['name']?.toString() ?? 'Workspace'),
          )).toList(),
          onChanged: (id) { if (id != null) run(() => switchWorkspace(id)); },
        ),
        const SizedBox(height: 20),
        const SectionHeader('PROJECTS'),
        if (projects.isEmpty) const EmptyLine('Projects saved to your cloud workspace will appear here.')
        else ...projects.map((p) => DataLine(
          title: p['name']?.toString() ?? 'Project',
          subtitle: p['description']?.toString() ?? '',
          trailing: p['status']?.toString(),
          icon: Icons.folder_open,
        )),
        const SizedBox(height: 16),
        const SectionHeader('ALERTS'),
        if (alerts.isEmpty) const EmptyLine('No alerts have been recorded.')
        else ...alerts.map((a) => DataLine(
          title: a['title']?.toString() ?? 'Alert',
          subtitle: a['summary']?.toString() ?? '',
          trailing: a['status']?.toString(),
          icon: Icons.notifications_active_outlined,
        )),
      ]),
      ListView(padding: const EdgeInsets.all(20), children: [
        const Text('YOUR DEVICES', style: TextStyle(color: accent, letterSpacing: 1.5, fontSize: 11, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        const Text('One JARVIS. All your devices.', style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        const Text('Review devices registered by your account. You can revoke a device if you no longer trust it.', style: TextStyle(color: muted, height: 1.5)),
        const SizedBox(height: 16),
        SectionHeader('REGISTERED DEVICES', onRefresh: () => run(refreshData)),
        if (devices.isEmpty) const EmptyLine('No active devices were returned by the cloud service.')
        else ...devices.map((d) => Card(
          color: panel,
          child: ListTile(
            leading: const Icon(Icons.devices, color: accent),
            title: Text(d['device_name']?.toString() ?? 'Device'),
            subtitle: Text('${d['platform'] ?? ''} • ${d['app_version'] ?? ''}'),
            trailing: IconButton(
              icon: const Icon(Icons.block, color: Colors.orangeAccent),
              tooltip: 'Revoke device',
              onPressed: () => run(() async {
                await client.revokeDevice(d['id'].toString());
                final deviceStorageKey = 'jarvis_registered_device_id_$workspaceId';
                final local = await storage.read(key: deviceStorageKey);
                if (local == d['id'].toString()) await storage.delete(key: deviceStorageKey);
                await refreshData();
              }),
            ),
          ),
        )),
        const SizedBox(height: 24),
        OutlinedButton.icon(onPressed: () => run(signOut), icon: const Icon(Icons.logout), label: const Text('Sign out')),
      ]),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Row(children: [
          Icon(Icons.auto_awesome, color: accent), SizedBox(width: 10),
          Text('JARVIS', style: TextStyle(fontWeight: FontWeight.w800, letterSpacing: 2)),
          SizedBox(width: 8),
          Text('MOBILE', style: TextStyle(color: muted, fontSize: 10)),
        ]),
        actions: [if (busy) const Padding(
          padding: EdgeInsets.all(16), child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
        ) else IconButton(onPressed: () => run(refreshData), icon: const Icon(Icons.refresh))],
      ),
      body: SafeArea(child: pages[tab]),
      bottomNavigationBar: NavigationBar(
        backgroundColor: panel, selectedIndex: tab,
        onDestinationSelected: (i) => setState(() => tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.grid_view), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.work_outline), label: 'Workspace'),
          NavigationDestination(icon: Icon(Icons.devices), label: 'Devices'),
        ],
      ),
    );
  }
}

class ConfigPage extends StatefulWidget {
  const ConfigPage({super.key, this.error, required this.busy, required this.onSave});
  final String? error; final bool busy;
  final Future<void> Function(String,String,String) onSave;
  @override State<ConfigPage> createState() => _ConfigPageState();
}
class _ConfigPageState extends State<ConfigPage> {
  final api = TextEditingController(), supa = TextEditingController(), key = TextEditingController();
  @override void dispose() { api.dispose(); supa.dispose(); key.dispose(); super.dispose(); }
  @override Widget build(BuildContext context) => AuthLayout(
    eyebrow: 'ONE ACCOUNT. ALL YOUR DEVICES.',
    title: 'Connect JARVIS',
    subtitle: 'Enter the cloud API and Supabase project details. They will be stored securely on this phone.',
    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      TextField(controller: api, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText: 'JARVIS cloud API HTTPS URL')),
      const SizedBox(height: 12),
      TextField(controller: supa, keyboardType: TextInputType.url, decoration: const InputDecoration(labelText: 'Supabase project HTTPS URL')),
      const SizedBox(height: 12),
      TextField(controller: key, obscureText: true, decoration: const InputDecoration(labelText: 'Supabase publishable / anon public key')),
      const SizedBox(height: 14),
      if (widget.error != null) ErrorLine(widget.error!),
      FilledButton(onPressed: widget.busy ? null : () => widget.onSave(api.text,supa.text,key.text), child: Text(widget.busy ? 'Connecting…' : 'Save and test cloud API')),
      const SizedBox(height: 12),
      const Text('Never enter a Supabase service-role key in a mobile app.', style: TextStyle(color: muted, fontSize: 12)),
    ]),
  );
}

class SignInPage extends StatefulWidget {
  const SignInPage({super.key, this.error, required this.busy, required this.onLogin, required this.onSignup});
  final String? error; final bool busy;
  final Future<void> Function(String,String) onLogin, onSignup;
  @override State<SignInPage> createState() => _SignInPageState();
}
class _SignInPageState extends State<SignInPage> {
  final email = TextEditingController(), password = TextEditingController();
  bool create = false;
  @override void dispose() { email.dispose(); password.dispose(); super.dispose(); }
  @override Widget build(BuildContext context) => AuthLayout(
    eyebrow: 'YOUR PERSONAL AI OPERATING SYSTEM',
    title: create ? 'Create your account.' : 'Welcome back.',
    subtitle: 'Sign in to open the same JARVIS workspace from your phone and Windows computer.',
    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      TextField(controller: email, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Email address')),
      const SizedBox(height: 12),
      TextField(controller: password, obscureText: true, decoration: const InputDecoration(labelText: 'Password')),
      const SizedBox(height: 14),
      if (widget.error != null) ErrorLine(widget.error!),
      FilledButton(
        onPressed: widget.busy ? null : () => create ? widget.onSignup(email.text,password.text) : widget.onLogin(email.text,password.text),
        child: Text(widget.busy ? 'Please wait…' : create ? 'Create account' : 'Sign in securely'),
      ),
      TextButton(onPressed: widget.busy ? null : () => setState(() => create = !create),
        child: Text(create ? 'Already have an account? Sign in' : 'New to JARVIS? Create an account')),
    ]),
  );
}

class CreateWorkspacePage extends StatefulWidget {
  const CreateWorkspacePage({super.key, this.error, required this.busy, required this.onCreate, required this.onSignOut});
  final String? error; final bool busy;
  final Future<void> Function(String) onCreate;
  final Future<void> Function() onSignOut;
  @override State<CreateWorkspacePage> createState() => _CreateWorkspacePageState();
}
class _CreateWorkspacePageState extends State<CreateWorkspacePage> {
  final name = TextEditingController(text: 'My JARVIS Workspace');
  @override void dispose() { name.dispose(); super.dispose(); }
  @override Widget build(BuildContext context) => AuthLayout(
    eyebrow: 'YOUR PRIVATE WORKSPACE',
    title: 'Set up your JARVIS.',
    subtitle: 'Create the shared workspace that your Windows desktop and mobile devices will use.',
    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      TextField(controller: name, decoration: const InputDecoration(labelText: 'Workspace name')),
      const SizedBox(height: 14),
      if (widget.error != null) ErrorLine(widget.error!),
      FilledButton(onPressed: widget.busy ? null : () => widget.onCreate(name.text), child: Text(widget.busy ? 'Creating…' : 'Create workspace')),
      TextButton(onPressed: widget.busy ? null : widget.onSignOut, child: const Text('Sign out')),
    ]),
  );
}

class AuthLayout extends StatelessWidget {
  const AuthLayout({super.key, required this.eyebrow, required this.title, required this.subtitle, required this.child});
  final String eyebrow,title,subtitle; final Widget child;
  @override Widget build(BuildContext context) => Scaffold(
    body: SafeArea(child: Center(child: SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 460), child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Icon(Icons.auto_awesome, color: accent, size: 42),
          const SizedBox(height: 28),
          Text(eyebrow, style: const TextStyle(color: accent, fontSize: 11, letterSpacing: 1.5, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          Text(title, style: const TextStyle(fontSize: 32, height: 1.12, fontWeight: FontWeight.w800)),
          const SizedBox(height: 10),
          Text(subtitle, style: const TextStyle(color: muted, height: 1.5)),
          const SizedBox(height: 26),
          child,
        ],
      )),
    ))),
  );
}

class Metric extends StatelessWidget {
  const Metric(this.title,this.value,this.icon,{super.key});
  final String title,value; final IconData icon;
  @override Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(color: panel,borderRadius: BorderRadius.circular(17)),
    child: Row(children: [
      Icon(icon,color: accent), const SizedBox(width: 10),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start,children: [
        Text(title,style: const TextStyle(color: muted,fontSize: 11)),
        const SizedBox(height: 4), Text(value,style: const TextStyle(fontSize: 22,fontWeight: FontWeight.w800)),
      ])),
    ]),
  );
}

class SectionHeader extends StatelessWidget {
  const SectionHeader(this.title,{super.key,this.onRefresh});
  final String title; final Future<void> Function()? onRefresh;
  @override Widget build(BuildContext context) => Row(children: [
    Expanded(child: Text(title,style: const TextStyle(fontSize: 12,letterSpacing: 1.3,fontWeight: FontWeight.bold,color: muted))),
    if (onRefresh != null) TextButton(onPressed: onRefresh,child: const Text('Refresh')),
  ]);
}

class DataLine extends StatelessWidget {
  const DataLine({super.key,required this.title,required this.subtitle,required this.trailing,required this.icon});
  final String title,subtitle; final String? trailing; final IconData icon;
  @override Widget build(BuildContext context) => Card(
    color: panel, child: ListTile(
      leading: Icon(icon,color: accent), title: Text(title),
      subtitle: subtitle.isEmpty ? null : Text(subtitle,maxLines: 2,overflow: TextOverflow.ellipsis),
      trailing: trailing == null || trailing!.isEmpty ? null : Text(trailing!,style: const TextStyle(color: muted,fontSize: 11)),
    ),
  );
}

class EmptyLine extends StatelessWidget {
  const EmptyLine(this.text,{super.key}); final String text;
  @override Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 12),
    child: Text(text,style: const TextStyle(color: muted,height: 1.5)),
  );
}

class ErrorLine extends StatelessWidget {
  const ErrorLine(this.text,{super.key}); final String text;
  @override Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Text(text,style: const TextStyle(color: Colors.orangeAccent,height: 1.4)),
  );
}
