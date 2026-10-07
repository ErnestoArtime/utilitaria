import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://utilitaria-api.eav-labs.com',
);

class ApiException implements Exception {
  final int? statusCode;
  final String message;

  const ApiException(this.message, {this.statusCode});

  bool get isUnauthorized => statusCode == 401;

  @override
  String toString() => message;
}

class CacheStatus {
  final DateTime? updatedAt;
  final bool offline;
  final bool syncing;
  const CacheStatus({
    this.updatedAt,
    this.offline = false,
    this.syncing = false,
  });
}

class ApiClient {
  static const tokenKey = 'auth_token';

  final String baseUrl;
  final Duration requestTimeout;
  final http.Client _httpClient;
  final ValueNotifier<int> cacheChanges = ValueNotifier(0);
  final Map<String, CacheStatus> _statuses = {};

  ApiClient({
    this.baseUrl = apiBaseUrl,
    this.requestTimeout = const Duration(seconds: 4),
    http.Client? httpClient,
  }) : _httpClient = httpClient ?? http.Client();

  Future<String?> accessToken() async {
    final preferences = await SharedPreferences.getInstance();
    return preferences.getString(tokenKey);
  }

  Future<void> saveAccessToken(String token) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(tokenKey, token);
  }

  Future<void> clearAccessToken() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.remove(tokenKey);
  }

  Future<Map<String, String>> _headers({bool anonymous = false}) async {
    final token = anonymous ? null : await accessToken();
    return {
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  String _cacheKey(String path) =>
      base64Url.encode(utf8.encode(path)).replaceAll('=', '');

  CacheStatus status(String path) => _statuses[path] ?? const CacheStatus();

  void _setStatus(String path, CacheStatus status) {
    _statuses[path] = status;
    cacheChanges.value++;
  }

  ApiException _error(http.Response response) {
    String message = 'No se pudo completar la operación.';
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map && decoded['detail'] != null) {
        message = decoded['detail'].toString();
      }
    } catch (_) {
      // El servidor puede devolver HTML o una respuesta vacía.
    }
    if (response.statusCode == 401) {
      message = 'Este dispositivo necesita volver a activarse.';
    } else if (response.statusCode == 403) {
      message = 'Tu usuario no tiene permiso para realizar esta acción.';
    }
    return ApiException(message, statusCode: response.statusCode);
  }

  Future<dynamic> get(String path, {bool useCache = true}) async {
    final preferences = await SharedPreferences.getInstance();
    final key = _cacheKey(path);
    final savedAt = preferences.getInt('api_cache_time_$key');
    _setStatus(
      path,
      CacheStatus(
        updatedAt: savedAt == null
            ? null
            : DateTime.fromMillisecondsSinceEpoch(savedAt),
        syncing: true,
      ),
    );
    try {
      final response = await _httpClient
          .get(Uri.parse('$baseUrl$path'), headers: await _headers())
          .timeout(requestTimeout);
      if (response.statusCode >= 400) throw _error(response);
      final decoded = jsonDecode(response.body);
      final now = DateTime.now();
      if (useCache) {
        await preferences.setString('api_cache_body_$key', response.body);
        await preferences.setInt(
          'api_cache_time_$key',
          now.millisecondsSinceEpoch,
        );
      }
      _setStatus(path, CacheStatus(updatedAt: now));
      return decoded;
    } on ApiException catch (error) {
      if (error.isUnauthorized || !useCache) rethrow;
      return _cachedOrThrow(preferences, key, path, error);
    } catch (error) {
      if (!useCache) rethrow;
      return _cachedOrThrow(preferences, key, path, error);
    }
  }

  dynamic _cachedOrThrow(
    SharedPreferences preferences,
    String key,
    String path,
    Object error,
  ) {
    final cachedBody = preferences.getString('api_cache_body_$key');
    final cachedAt = preferences.getInt('api_cache_time_$key');
    _setStatus(
      path,
      CacheStatus(
        updatedAt: cachedAt == null
            ? null
            : DateTime.fromMillisecondsSinceEpoch(cachedAt),
        offline: true,
      ),
    );
    if (cachedBody != null) return jsonDecode(cachedBody);
    throw error;
  }

  Future<dynamic> post(
    String path,
    Map<String, dynamic> body, {
    bool anonymous = false,
  }) async {
    final response = await _httpClient
        .post(
          Uri.parse('$baseUrl$path'),
          headers: {
            ...await _headers(anonymous: anonymous),
            'Content-Type': 'application/json',
          },
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 12));
    if (response.statusCode >= 400) throw _error(response);
    return jsonDecode(response.body);
  }

  Future<dynamic> patch(String path, Map<String, dynamic> body) async {
    final response = await _httpClient
        .patch(
          Uri.parse('$baseUrl$path'),
          headers: {
            ...await _headers(),
            'Content-Type': 'application/json',
          },
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 12));
    if (response.statusCode >= 400) throw _error(response);
    return jsonDecode(response.body);
  }

  Future<void> delete(String path) async {
    final response = await _httpClient
        .delete(Uri.parse('$baseUrl$path'), headers: await _headers())
        .timeout(const Duration(seconds: 12));
    if (response.statusCode >= 400) throw _error(response);
  }
}

String readableApiError(Object error) {
  if (error is ApiException) return error.message;
  return 'No se pudo conectar. Comprueba la conexión e inténtalo de nuevo.';
}

final api = ApiClient();
