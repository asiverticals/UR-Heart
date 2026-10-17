import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/services/device_fingerprint_service.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/auth/presentation/controllers/auth_controller.dart';

class TestSecureStorage extends Fake implements FlutterSecureStorage {
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

class FakeHttpClient extends Fake implements http.Client {
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

class FakeFingerprintService extends Fake implements DeviceFingerprintService {
  @override
  Future<String> getOrCreateFingerprint() async => 'fake-fingerprint-m1-adversarial';
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Adversarial Stress Test: Client Fail-Safe Teardown & Error Matrix', () {
    test(
      'ADV 1: SanctuaryHttpClient.logout sweeps hardware vault under exhaustive error matrix',
      () async {
        final errorScenarios = <String, Future<http.Response> Function()>{
          'HTTP 500 JSON error': () async => http.Response(
                jsonEncode({'error_code': 'INTERNAL_ERROR', 'message': 'DB crash'}),
                500,
              ),
          'HTTP 500 HTML raw text': () async => http.Response(
                '<!DOCTYPE html><html><body>500 Internal Server Error</body></html>',
                500,
              ),
          'HTTP 502 Bad Gateway': () async => http.Response('Bad Gateway', 502),
          'HTTP 504 Gateway Timeout': () async => http.Response('Gateway Timeout', 504),
          'HTTP 401 TOKEN_REVOKED': () async => http.Response(
                jsonEncode({'error_code': 'TOKEN_REVOKED', 'message': 'Already revoked'}),
                401,
              ),
          'HTTP 429 Rate Limited': () async => http.Response(
                jsonEncode({'error_code': 'TOO_MANY_REQUESTS'}),
                429,
              ),
          'SocketException Offline': () async => throw const SocketException('No route to host'),
          'ClientException Reset': () async => throw http.ClientException('Connection reset by peer'),
          'TimeoutException': () async => throw TimeoutException('Request timed out'),
          'FormatException': () async => throw const FormatException('Corrupted response payload'),
        };

        for (final entry in errorScenarios.entries) {
          final desc = entry.key;
          final errorProducer = entry.value;

          final fakeStorage = TestSecureStorage();
          final sessionStorage = SecureSessionStorage(storage: fakeStorage);

          await sessionStorage.persistSession(
            accessToken: 'active-token-under-test',
            refreshToken: 'active-refresh-under-test',
            userId: 'user-adversarial-1',
            role: 'user',
          );

          final mockClient = FakeHttpClient();
          mockClient.onPost = (url, headers, body) async {
            if (url.path == '/api/v1/auth/logout') {
              return errorProducer();
            }
            return http.Response('{}', 200);
          };

          final client = SanctuaryHttpClient(sessionStorage, client: mockClient);

          // Crucial check: client.logout() must NOT throw and must unconditionally wipe storage
          await expectLater(client.logout(), completes, reason: 'Failed on $desc');

          expect(await sessionStorage.readAuthToken(), isNull, reason: '$desc failed to clear authToken');
          expect(await sessionStorage.readRefreshToken(), isNull, reason: '$desc failed to clear refreshToken');
          expect(await sessionStorage.readUserId(), isNull, reason: '$desc failed to clear userId');
        }
      },
    );

    test(
      'ADV 2: AuthController.signOut handles exhaustive error matrix and guarantees Riverpod teardown',
      () async {
        final errorScenarios = <String, Future<http.Response> Function()>{
          'HTTP 500 Database down': () async => http.Response(
                jsonEncode({'error_code': 'DB_DOWN'}),
                500,
              ),
          'HTTP 401 Session already revoked': () async => http.Response(
                jsonEncode({'error_code': 'TOKEN_REVOKED'}),
                401,
              ),
          'ClientException Dropped Connection': () async => throw http.ClientException('Dropped connection'),
          'TimeoutException': () async => throw TimeoutException('Timeout 30s'),
          'SocketException DNS fail': () async => throw const SocketException('DNS resolution failed'),
        };

        for (final entry in errorScenarios.entries) {
          final desc = entry.key;
          final errorProducer = entry.value;

          final fakeStorage = TestSecureStorage();
          final sessionStorage = SecureSessionStorage(storage: fakeStorage);

          await sessionStorage.persistSession(
            accessToken: 'session-token-$desc',
            refreshToken: 'refresh-token-$desc',
            userId: 'user-$desc',
            role: 'user',
          );

          final mockClient = FakeHttpClient();
          mockClient.onPost = (url, headers, body) async {
            if (url.path == '/api/v1/auth/logout') {
              return errorProducer();
            }
            return http.Response('{}', 200);
          };

          final client = SanctuaryHttpClient(sessionStorage, client: mockClient);
          final container = ProviderContainer(
            overrides: [
              secureSessionStorageProvider.overrideWithValue(sessionStorage),
              sanctuaryHttpClientProvider.overrideWithValue(client),
              deviceFingerprintServiceProvider.overrideWithValue(FakeFingerprintService()),
            ],
          );

          container.read(currentUserProvider.notifier).state = CurrentUser(
            id: 'user-$desc',
            role: 'user',
          );

          final controller = container.read(authControllerProvider.notifier);

          // Execute signOut
          await expectLater(controller.signOut(), completes, reason: 'SignOut threw on $desc');

          // Vault wiped
          expect(await sessionStorage.readAuthToken(), isNull, reason: '$desc did not wipe auth token');
          expect(await sessionStorage.readRefreshToken(), isNull, reason: '$desc did not wipe refresh token');

          // Riverpod state reset
          expect(container.read(currentUserProvider), isNull, reason: '$desc did not clear currentUser');
          final finalState = container.read(authControllerProvider);
          expect(finalState.isLoading, isFalse, reason: '$desc left isLoading: true');
          expect(finalState.errorMessage, isNull, reason: '$desc left error message');

          container.dispose();
        }
      },
    );

    test(
      'ADV 3: Rapid multi-tap concurrent signOut calls converge without deadlock or residual session',
      () async {
        final fakeStorage = TestSecureStorage();
        final sessionStorage = SecureSessionStorage(storage: fakeStorage);

        await sessionStorage.persistSession(
          accessToken: 'multi-tap-token',
          refreshToken: 'multi-tap-refresh',
          userId: 'user-multitap',
          role: 'user',
        );

        int logoutCallCount = 0;
        final mockClient = FakeHttpClient();
        mockClient.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/auth/logout') {
            logoutCallCount++;
            // Simulate variable latency
            await Future.delayed(const Duration(milliseconds: 10));
            return http.Response(
              jsonEncode({
                'success': true,
                'data': {'revoked': true, 'token_version': 2},
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        };

        final client = SanctuaryHttpClient(sessionStorage, client: mockClient);
        final container = ProviderContainer(
          overrides: [
            secureSessionStorageProvider.overrideWithValue(sessionStorage),
            sanctuaryHttpClientProvider.overrideWithValue(client),
            deviceFingerprintServiceProvider.overrideWithValue(FakeFingerprintService()),
          ],
        );
        addTearDown(container.dispose);

        container.read(currentUserProvider.notifier).state = const CurrentUser(
          id: 'user-multitap',
          role: 'user',
        );

        final controller = container.read(authControllerProvider.notifier);

        // Simulate user tapping signOut 5 times in parallel
        await Future.wait([
          controller.signOut(),
          controller.signOut(),
          controller.signOut(),
          controller.signOut(),
          controller.signOut(),
        ]);

        // Verifications
        expect(logoutCallCount, greaterThanOrEqualTo(1));
        expect(await sessionStorage.readAuthToken(), isNull);
        expect(await sessionStorage.readRefreshToken(), isNull);
        expect(container.read(currentUserProvider), isNull);

        final state = container.read(authControllerProvider);
        expect(state.isLoading, isFalse);
        expect(state.errorMessage, isNull);
      },
    );

    test(
      'ADV 4: Token rotation resilience when server returns revoked refresh token or empty fields',
      () async {
        final fakeStorage = TestSecureStorage();
        final sessionStorage = SecureSessionStorage(storage: fakeStorage);

        await sessionStorage.persistSession(
          accessToken: 'stale-access-token',
          refreshToken: 'stale-refresh-token',
          userId: 'user-stale',
          role: 'user',
        );

        final mockClient = FakeHttpClient();
        bool refreshCalled = false;

        mockClient.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/auth/refresh') {
            refreshCalled = true;
            // Server responds that refresh token has been revoked
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
          // Protected route returns 401 first
          return http.Response(
            jsonEncode({
              'success': false,
              'error_code': 'TOKEN_REVOKED',
              'message': 'Session revoked',
            }),
            401,
          );
        };

        final client = SanctuaryHttpClient(sessionStorage, client: mockClient);

        // Making a GET call will trigger 401, then attempt refresh, which fails with 401
        await expectLater(
          client.get('/api/v1/feed'),
          throwsA(isA<SanctuaryClientException>().having(
            (e) => e.statusCode,
            'statusCode',
            401,
          )),
        );
        expect(refreshCalled, isTrue);
        // Also verify that failing token refresh triggers automatic session clearance in client
        expect(await sessionStorage.readAuthToken(), isNull);
        expect(await sessionStorage.readRefreshToken(), isNull);
      },
    );

    test(
      'ADV 5: Partial token rotation does not wipe existing refresh token if missing from response',
      () async {
        final fakeStorage = TestSecureStorage();
        final sessionStorage = SecureSessionStorage(storage: fakeStorage);

        await sessionStorage.persistSession(
          accessToken: 'initial-access-token',
          refreshToken: 'initial-refresh-token',
          userId: 'user-partial',
          role: 'user',
        );

        final mockClient = FakeHttpClient();
        mockClient.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/auth/refresh') {
            // Server returns new access token but no refresh token
            return http.Response(
              jsonEncode({
                'success': true,
                'data': {
                  'access_token': 'new-single-access-token',
                  // refresh_token is absent
                },
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        };

        int getCount = 0;
        mockClient.onGet = (url, headers) async {
          getCount++;
          if (getCount == 1) {
            // First call triggers refresh
            return http.Response(
              jsonEncode({'error_code': 'TOKEN_EXPIRED'}),
              401,
            );
          }
          // Retry succeeds
          return http.Response(
            jsonEncode({'success': true, 'data': {}}),
            200,
          );
        };

        final client = SanctuaryHttpClient(sessionStorage, client: mockClient);
        final res = await client.get('/api/v1/profile/me');
        expect(res['success'], isTrue);

        // Access token was updated
        expect(await sessionStorage.readAuthToken(), 'new-single-access-token');
        // Initial refresh token was NOT wiped or set to null/empty
        expect(await sessionStorage.readRefreshToken(), 'initial-refresh-token');
      },
    );
  });
}
