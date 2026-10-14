import 'dart:async';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../storage/secure_session_storage.dart';

final sanctuaryHttpClientProvider = Provider<SanctuaryHttpClient>((ref) {
  final storage = ref.watch(secureSessionStorageProvider);
  return SanctuaryHttpClient(storage);
});

class SanctuaryHttpClient {
  static const String baseUrl = 'https://urheart.app';
  static const Duration defaultTimeout = Duration(seconds: 15);

  final SecureSessionStorage _storage;
  final http.Client _client;
  final Duration requestTimeout;
  Future<bool>? _inFlightRefresh;

  SanctuaryHttpClient(
    this._storage, {
    http.Client? client,
    this.requestTimeout = defaultTimeout,
  }) : _client = client ?? http.Client();

  Future<Map<String, dynamic>> get(String path) async {
    return _sendRequest('GET', path);
  }

  Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    return _sendRequest('POST', path, body: body);
  }

  Future<Map<String, dynamic>> delete(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    return _sendRequest('DELETE', path, body: body);
  }

  Future<Map<String, dynamic>> put(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    return _sendRequest('PUT', path, body: body);
  }

  Future<bool> _performTokenRefresh() async {
    final refreshToken = await _storage.readRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) return false;
    try {
      final refreshed = await post(
        '/api/v1/auth/refresh',
        body: {'refresh_token': refreshToken},
      );
      final newAccessToken = refreshed['data']?['access_token'] ??
          refreshed['access_token'];
      if (newAccessToken is String && newAccessToken.isNotEmpty) {
        await _storage.saveAuthToken(newAccessToken);
        return true;
      }
    } on SanctuaryClientException catch (e) {
      if (e.statusCode == 401 || e.statusCode == 403) {
        return false;
      }
      rethrow;
    }
    return false;
  }

  Future<Map<String, dynamic>> _sendRequest(
    String method,
    String path, {
    Map<String, dynamic>? body,
    bool isRetry = false,
  }) async {
    final token = await _storage.readAuthToken();
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
    };

    final uri = Uri.parse('$baseUrl$path');
    http.Response response;

    try {
      switch (method) {
        case 'GET':
          response = await _client.get(uri, headers: headers).timeout(requestTimeout);
          break;
        case 'POST':
          response = await _client.post(
            uri,
            headers: headers,
            body: jsonEncode(body ?? {}),
          ).timeout(requestTimeout);
          break;
        case 'DELETE':
          response = await _client.delete(
            uri,
            headers: headers,
            body: jsonEncode(body ?? {}),
          ).timeout(requestTimeout);
          break;
        case 'PUT':
          response = await _client.put(
            uri,
            headers: headers,
            body: jsonEncode(body ?? {}),
          ).timeout(requestTimeout);
          break;
        default:
          throw UnsupportedError('Unsupported HTTP method: $method');
      }
    } on TimeoutException {
      throw const SanctuaryClientException(
        statusCode: 408,
        errorCode: 'REQUEST_TIMEOUT',
        message: 'Network request timed out',
      );
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return <String, dynamic>{};
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
      return <String, dynamic>{'data': decoded};
    } else if (response.statusCode == 401 &&
        path != '/api/v1/auth/refresh' &&
        !isRetry) {
      Future<bool> refreshFuture;
      if (_inFlightRefresh != null) {
        refreshFuture = _inFlightRefresh!;
      } else {
        refreshFuture = _inFlightRefresh = _performTokenRefresh();
      }

      bool refreshSucceeded = false;
      try {
        refreshSucceeded = await refreshFuture;
      } finally {
        if (_inFlightRefresh == refreshFuture) {
          _inFlightRefresh = null;
        }
      }

      if (refreshSucceeded) {
        return _sendRequest(method, path, body: body, isRetry: true);
      }

      await _storage.clearSession();
      final errorBody = _parseErrorBody(response.body);
      throw SanctuaryClientException(
        statusCode: response.statusCode,
        errorCode: errorBody['error_code'] ?? 'AUTH_EXPIRED',
        message: errorBody['message'] ?? 'Session expired',
      );
    } else {
      final errorBody = _parseErrorBody(response.body);
      throw SanctuaryClientException(
        statusCode: response.statusCode,
        errorCode: errorBody['error_code'] ?? 'UNKNOWN_ERROR',
        message: errorBody['message'] ?? 'Network request failed',
      );
    }
  }

  Map<String, dynamic> _parseErrorBody(String body) {
    if (body.isEmpty) return <String, dynamic>{};
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
      return <String, dynamic>{'message': body};
    } catch (_) {
      return <String, dynamic>{'message': body};
    }
  }
}

class SanctuaryClientException implements Exception {
  final int statusCode;
  final String errorCode;
  final String message;

  const SanctuaryClientException({
    required this.statusCode,
    required this.errorCode,
    required this.message,
  });

  @override
  String toString() => '[$errorCode ($statusCode)]: $message';
}
