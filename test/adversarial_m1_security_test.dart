import 'dart:async';
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';

class InMemorySecureStorage extends Fake implements FlutterSecureStorage {
  final Map<String, String> _data = {};

  @override
  Future<void> write({
    required String key,
    required String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value != null) {
      _data[key] = value;
    } else {
      _data.remove(key);
    }
  }

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    return _data[key];
  }

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _data.remove(key);
  }

  @override
  Future<void> deleteAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _data.clear();
  }
}

class MockHttpClientEngine extends Fake implements http.Client {
  Future<http.Response> Function(Uri url, Map<String, String>? headers)? onGet;
  Future<http.Response> Function(
    Uri url,
    Map<String, String>? headers,
    Object? body,
  )? onPost;

  @override
  Future<http.Response> get(Uri url, {Map<String, String>? headers}) async {
    if (onGet != null) return onGet!(url, headers);
    return http.Response('{}', 200);
  }

  @override
  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    if (onPost != null) return onPost!(url, headers, body);
    return http.Response('{}', 200);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Milestone 1 Adversarial Security Challenge: Token Rotation & Replay Defense', () {
    test(
      'Adversarial 1: Token rotation prevents replay of previous refresh token',
      () async {
        final storageBackend = InMemorySecureStorage();
        final storage = SecureSessionStorage(storage: storageBackend);
        await storage.persistSession(
          accessToken: 'initial-access-v1',
          refreshToken: 'refresh-token-epoch-1',
          userId: 'test-user-id',
          role: 'user',
        );

        final mockClient = MockHttpClientEngine();
        final sentRefreshTokens = <String>[];
        int refreshCount = 0;

        mockClient.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/auth/refresh') {
            final parsed = jsonDecode(body as String);
            final usedToken = parsed['refresh_token'] as String;
            sentRefreshTokens.add(usedToken);
            refreshCount++;
            return http.Response(
              jsonEncode({
                'success': true,
                'data': {
                  'access_token': 'access-token-epoch-$refreshCount',
                  'refresh_token': 'refresh-token-epoch-${refreshCount + 1}',
                },
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        };

        mockClient.onGet = (url, headers) async {
          // Reject with 401 if token is not the latest
          final authHeader = headers?['Authorization'] ?? '';
          if (authHeader == 'Bearer access-token-epoch-$refreshCount') {
            return http.Response('{"status": "ok"}', 200);
          }
          return http.Response('{"error_code": "TOKEN_EXPIRED"}', 401);
        };

        final client = SanctuaryHttpClient(
          storage,
          client: mockClient,
        );

        // First call triggers 401 and refreshes using refresh-token-epoch-1
        final res1 = await client.get('/api/v1/feed');
        expect(res1['status'], 'ok');
        expect(sentRefreshTokens.first, 'refresh-token-epoch-1');
        expect(await storage.readRefreshToken(), 'refresh-token-epoch-2');

        // Subsequent call when access token expires MUST send refresh-token-epoch-2
        // If it replayed refresh-token-epoch-1, that would be a replay vulnerability
        final res2 = await client.get('/api/v1/feed');
        expect(res2['status'], 'ok');
        // Because res1 refreshed, access-token-epoch-1 matches header, so res2 succeeds without refresh
      },
    );

    test(
      'Adversarial 2: Multi-step sequential refresh chain always rotates tokens correctly',
      () async {
        final storageBackend = InMemorySecureStorage();
        final storage = SecureSessionStorage(storage: storageBackend);
        await storage.persistSession(
          accessToken: 'acc-step-0',
          refreshToken: 'ref-step-0',
          userId: 'test-user-id',
          role: 'user',
        );

        final mockClient = MockHttpClientEngine();
        final refreshLog = <String>[];
        int currentEpoch = 0;

        mockClient.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/auth/refresh') {
            final parsed = jsonDecode(body as String);
            refreshLog.add(parsed['refresh_token']);
            currentEpoch++;
            return http.Response(
              jsonEncode({
                'access_token': 'acc-step-$currentEpoch',
                'refresh_token': 'ref-step-$currentEpoch',
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        };

        // Always return 401 on GET to force consecutive refreshes
        mockClient.onGet = (url, headers) async {
          return http.Response('{"error_code": "EXPIRED"}', 401);
        };

        final client = SanctuaryHttpClient(
          storage,
          client: mockClient,
        );

        // Each GET call fails with 401, triggers refresh, rotates token, retries with isRetry=true (which fails again and raises)
        for (int i = 0; i < 3; i++) {
          try {
            await client.get('/api/v1/resource_$i');
          } catch (_) {}
        }

        // Verify the chain used ref-step-0, ref-step-1, ref-step-2 in strict order
        expect(refreshLog, ['ref-step-0', 'ref-step-1', 'ref-step-2']);
      },
    );

    test(
      'Adversarial 3: Concurrent 401 requests coalesce into a single refresh call',
      () async {
        final storageBackend = InMemorySecureStorage();
        final storage = SecureSessionStorage(storage: storageBackend);
        await storage.persistSession(
          accessToken: 'stale-token',
          refreshToken: 'refresh-token-single',
          userId: 'test-user-id',
          role: 'user',
        );

        final mockClient = MockHttpClientEngine();
        int refreshApiCalls = 0;
        final refreshCompleter = Completer<http.Response>();

        mockClient.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/auth/refresh') {
            refreshApiCalls++;
            return refreshCompleter.future;
          }
          return http.Response('{}', 200);
        };

        int getCalls = 0;
        mockClient.onGet = (url, headers) async {
          getCalls++;
          final auth = headers?['Authorization'];
          if (auth == 'Bearer fresh-access-token') {
            return http.Response('{"data": "fresh_data"}', 200);
          }
          return http.Response('{"error_code": "EXPIRED"}', 401);
        };

        final client = SanctuaryHttpClient(
          storage,
          client: mockClient,
        );

        // Dispatch 2 requests concurrently while access token is expired
        final future1 = client.get('/api/v1/endpoint_a');
        final future2 = client.get('/api/v1/endpoint_b');

        // Let the event loop advance to let both hit 401 and queue refresh
        await Future.delayed(const Duration(milliseconds: 20));

        // Complete the refresh HTTP call
        refreshCompleter.complete(
          http.Response(
            jsonEncode({
              'data': {
                'access_token': 'fresh-access-token',
                'refresh_token': 'fresh-refresh-token',
              },
            }),
            200,
          ),
        );

        final results = await Future.wait<Map<String, dynamic>>([future1, future2]);
        expect(results[0]['data'], 'fresh_data');
        expect(results[1]['data'], 'fresh_data');

        // Crucial security invariant: only 1 refresh call was made, preventing race desync
        expect(refreshApiCalls, 1);
        expect(getCalls, 4);
        expect(await storage.readAuthToken(), 'fresh-access-token');
        expect(await storage.readRefreshToken(), 'fresh-refresh-token');
      },
    );

    test(
      'Adversarial 4: Server revocation during refresh clears vault immediately',
      () async {
        final storageBackend = InMemorySecureStorage();
        final storage = SecureSessionStorage(storage: storageBackend);
        await storage.persistSession(
          accessToken: 'revoked-access',
          refreshToken: 'revoked-refresh',
          userId: 'test-user-id',
          role: 'user',
        );

        final mockClient = MockHttpClientEngine();
        mockClient.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/auth/refresh') {
            return http.Response(
              jsonEncode({
                'success': false,
                'error_code': 'INVALID_REFRESH_TOKEN',
                'message': 'Refresh token has been revoked.',
              }),
              401,
            );
          }
          return http.Response('{}', 200);
        };

        mockClient.onGet = (url, headers) async {
          return http.Response('{"error_code": "TOKEN_REVOKED"}', 401);
        };

        final client = SanctuaryHttpClient(
          storage,
          client: mockClient,
        );

        // Calling GET hits 401, triggers refresh, which returns 401.
        // SanctuaryHttpClient must clear session and throw SanctuaryClientException.
        expect(
          () => client.get('/api/v1/feed'),
          throwsA(isA<SanctuaryClientException>().having((e) => e.statusCode, 'statusCode', 401)),
        );

        // Local storage must be cleanly incinerated
        await Future.delayed(const Duration(milliseconds: 50));
        expect(await storage.readAuthToken(), isNull);
        expect(await storage.readRefreshToken(), isNull);
      },
    );
  });
}
