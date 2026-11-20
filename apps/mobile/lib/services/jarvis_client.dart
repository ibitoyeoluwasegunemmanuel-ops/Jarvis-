import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class JarvisClient {
  JarvisClient({http.Client? httpClient})
      : _http = httpClient ?? http.Client();

  static const _storage = FlutterSecureStorage();
  final http.Client _http;

  String _apiUrl = '';
  String _supabaseUrl = '';
  String _publicKey = '';
  String? _accessToken;
  String? _refreshToken;
  int _expiresAt = 0;

  bool get isConfigured =>
      _apiUrl.isNotEmpty && _supabaseUrl.isNotEmpty && _publicKey.isNotEmpty;
  bool get isSignedIn => (_accessToken?.isNotEmpty ?? false) && (_refreshToken?.isNotEmpty ?? false);
  String get apiUrl => _apiUrl;

  Future<void> load() async {
    _apiUrl = await _storage.read(key: 'jarvis_api_base_url') ?? '';
    _supabaseUrl = await _storage.read(key: 'jarvis_supabase_url') ?? '';
    _publicKey = await _storage.read(key: 'jarvis_supabase_public_key') ?? '';
    _accessToken = await _storage.read(key: 'jarvis_access_token');
    _refreshToken = await _storage.read(key: 'jarvis_refresh_token');
    _expiresAt = int.tryParse(
          await _storage.read(key: 'jarvis_token_expires_at') ?? '',
        ) ??
        0;
  }

  Future<void> saveConfiguration({
    required String apiUrl,
    required String supabaseUrl,
    required String publicKey,
  }) async {
    final api = _normaliseHttps(apiUrl, 'JARVIS API');
    final supabase = _normaliseHttps(supabaseUrl, 'Supabase');
    if (publicKey.trim().isEmpty) {
      throw const JarvisException('Enter the Supabase publishable/anon public key.');
    }
    _apiUrl = api;
    _supabaseUrl = supabase;
    _publicKey = publicKey.trim();
    await _storage.write(key: 'jarvis_api_base_url', value: _apiUrl);
    await _storage.write(key: 'jarvis_supabase_url', value: _supabaseUrl);
    await _storage.write(key: 'jarvis_supabase_public_key', value: _publicKey);
  }

  String _normaliseHttps(String raw, String label) {
    final value = raw.trim().replaceFirst(RegExp(r'/+$'), '');
    final uri = Uri.tryParse(value);
    if (uri == null || uri.scheme != 'https' || uri.host.isEmpty) {
      throw JarvisException('$label address must be a valid HTTPS URL.');
    }
    return value;
  }

  Future<void> testCloudApi() async {
    final response = await _http
        .get(Uri.parse('$_apiUrl/health'))
        .timeout(const Duration(seconds: 12));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw JarvisException('JARVIS API health check failed (HTTP ${response.statusCode}).');
    }
  }

  Future<void> signIn(String email, String password) async {
    final response = await _authPost(
      '/auth/v1/token?grant_type=password',
      {'email': email.trim(), 'password': password},
    );
    await _acceptSession(response);
  }

  Future<bool> signUp(String email, String password) async {
    final response = await _authPost(
      '/auth/v1/signup',
      {'email': email.trim(), 'password': password},
    );
    if (response['access_token'] is String &&
        response['refresh_token'] is String) {
      await _acceptSession(response);
      return true;
    }
    return false; // Email confirmation may be required by the Supabase project.
  }

  Future<Map<String, dynamic>> _authPost(
    String path,
    Map<String, dynamic> body,
  ) async {
    if (!isConfigured) {
      throw const JarvisException('Configure the cloud API and Supabase project first.');
    }
    final response = await _http
        .post(
          Uri.parse('$_supabaseUrl$path'),
          headers: {
            'apikey': _publicKey,
            'Content-Type': 'application/json',
          },
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 15));
    final decoded = _decode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw JarvisException(_message(decoded, 'Authentication failed.'), statusCode: response.statusCode);
    }
    return decoded;
  }

  Future<void> _acceptSession(Map<String, dynamic> data) async {
    final access = data['access_token'];
    final refresh = data['refresh_token'];
    if (access is! String || access.isEmpty || refresh is! String || refresh.isEmpty) {
      throw const JarvisException(
        'No active session was returned. Check whether email confirmation is required.',
      );
    }
    _accessToken = access;
    _refreshToken = refresh;
    final expiresIn = (data['expires_in'] as num?)?.toInt() ?? 3600;
    _expiresAt = DateTime.now().millisecondsSinceEpoch ~/ 1000 + expiresIn;
    await _storage.write(key: 'jarvis_access_token', value: access);
    await _storage.write(key: 'jarvis_refresh_token', value: refresh);
    await _storage.write(
      key: 'jarvis_token_expires_at',
      value: _expiresAt.toString(),
    );
  }

  Future<void> _refreshSession() async {
    final refresh = _refreshToken;
    if (refresh == null) throw const JarvisException('Please sign in again.');
    try {
      final response = await _authPost(
        '/auth/v1/token?grant_type=refresh_token',
        {'refresh_token': refresh},
      );
      await _acceptSession(response);
    } on JarvisException catch (error) {
      if (error.statusCode == 400 || error.statusCode == 401) {
        await _clearLocalSession();
      }
      rethrow;
    }
  }

  Future<String> _validToken() async {
    if (_accessToken == null) throw const JarvisException('Please sign in.');
    final now = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    if (_expiresAt <= now + 60) {
      await _refreshSession();
    }
    return _accessToken!;
  }

  Future<dynamic> get(String path, {Map<String, String>? query}) async {
    return _apiRequest('GET', path, query: query);
  }

  Future<dynamic> post(String path, Map<String, dynamic> body) async {
    return _apiRequest('POST', path, body: body);
  }

  Future<dynamic> delete(String path) async {
    return _apiRequest('DELETE', path);
  }

  Future<dynamic> _apiRequest(
    String method,
    String path, {
    Map<String, String>? query,
    Map<String, dynamic>? body,
    bool retry = true,
  }) async {
    final token = await _validToken();
    final uri = Uri.parse('$_apiUrl$path').replace(queryParameters: query);
    final headers = {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    late http.Response response;
    try {
      switch (method) {
        case 'POST':
          response = await _http.post(uri, headers: headers, body: jsonEncode(body));
          break;
        case 'DELETE':
          response = await _http.delete(uri, headers: headers);
          break;
        default:
          response = await _http.get(uri, headers: headers);
          break;
      }
    } on Exception {
      rethrow;
    }
    if (response.statusCode == 401 && retry) {
      await _refreshSession();
      return _apiRequest(method, path, query: query, body: body, retry: false);
    }
    if (response.statusCode == 401) {
      await _clearLocalSession();
    }
    final decoded = _decode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw JarvisException(_message(decoded, 'JARVIS request failed (HTTP ${response.statusCode}).'));
    }
    return decoded;
  }

  Future<List<dynamic>> workspaces() async {
    final value = await get('/v1/workspaces');
    return value as List<dynamic>;
  }

  Future<Map<String, dynamic>> createWorkspace(String name) async {
    return await post('/v1/workspaces', {'name': name}) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> registerDevice({
    required String workspaceId,
    required String deviceName,
    required String platform,
  }) async {
    return await post('/v1/devices', {
      'workspace_id': workspaceId,
      'device_name': deviceName,
      'platform': platform,
      'app_version': '0.1.0',
    }) as Map<String, dynamic>;
  }

  Future<List<dynamic>> devices(String workspaceId) async {
    return await get('/v1/devices', query: {'workspace_id': workspaceId})
        as List<dynamic>;
  }

  Future<Map<String, dynamic>> overview(String workspaceId) async {
    return await get(
      '/v1/workspace/overview',
      query: {'workspace_id': workspaceId},
    ) as Map<String, dynamic>;
  }

  Future<List<dynamic>> projects(String workspaceId) async {
    return await get('/v1/projects', query: {'workspace_id': workspaceId})
        as List<dynamic>;
  }

  Future<List<dynamic>> alerts(String workspaceId) async {
    return await get(
      '/v1/monitoring/alerts',
      query: {'workspace_id': workspaceId},
    ) as List<dynamic>;
  }

  Future<List<dynamic>> memories(String workspaceId, {String? category}) async {
    return await get(
      '/v1/memory',
      query: {
        'workspace_id': workspaceId,
        if (category != null && category.isNotEmpty) 'category': category,
      },
    ) as List<dynamic>;
  }

  Future<Map<String, dynamic>> createMemory({
    required String workspaceId,
    required String category,
    required String content,
    String sourceRef = '',
  }) async {
    return await post('/v1/memory', {
      'workspace_id': workspaceId,
      'category': category,
      'content': content,
      'source_ref': sourceRef,
    }) as Map<String, dynamic>;
  }

  Future<void> heartbeatDevice(String deviceId) async {
    await post('/v1/devices/$deviceId/heartbeat', {});
  }

  Future<void> revokeDevice(String deviceId) async {
    await delete('/v1/devices/$deviceId');
  }

  Future<void> _clearLocalSession() async {
    _accessToken = null;
    _refreshToken = null;
    _expiresAt = 0;
    await _storage.delete(key: 'jarvis_access_token');
    await _storage.delete(key: 'jarvis_refresh_token');
    await _storage.delete(key: 'jarvis_token_expires_at');
  }

  Future<void> signOut() async {
    final token = _accessToken;
    if (token != null && _supabaseUrl.isNotEmpty) {
      try {
        await _http.post(
          Uri.parse('$_supabaseUrl/auth/v1/logout'),
          headers: {
            'apikey': _publicKey,
            'Authorization': 'Bearer $token',
          },
        ).timeout(const Duration(seconds: 5));
      } catch (_) {
        // Local credential deletion must still happen when offline.
      }
    }
    await _clearLocalSession();
  }

  Map<String, dynamic> _decode(String body) {
    if (body.isEmpty) return <String, dynamic>{};
    try {
      final value = jsonDecode(body);
      if (value is Map<String, dynamic>) return value;
      return {'data': value};
    } on FormatException {
      return {'message': 'The server returned an unreadable response.'};
    }
  }

  String _message(Map<String, dynamic> data, String fallback) {
    for (final key in [
      'message',
      'msg',
      'error_description',
      'error',
      'detail',
    ]) {
      final value = data[key];
      if (value is String && value.trim().isNotEmpty) return value;
    }
    return fallback;
  }

  void dispose() => _http.close();
}

class JarvisException implements Exception {
  const JarvisException(this.message, {this.statusCode});
  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}
