import 'dart:async';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:ur_heart/core/app/app_router.dart';
import 'package:ur_heart/core/app/ur_heart_app.dart';
import 'package:ur_heart/core/billing/sanctuary_billing_service.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/auth/presentation/providers/auth_controller.dart';
import 'package:ur_heart/features/blind_date/presentation/controllers/blind_date_controller.dart';
import 'package:ur_heart/features/growth/presentation/controllers/growth_hub_controller.dart';
import 'package:ur_heart/features/legal_vault/presentation/controllers/vault_controller.dart';
import 'package:ur_heart/features/resonances/presentation/controllers/resonances_controller.dart';
import 'package:ur_heart/features/navigation/presentation/screens/sanctuary_navigation_shell.dart';
import 'package:ur_heart/features/admin/presentation/screens/superadmin_kyc_desk_screen.dart';

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

  final Set<String> failingDeleteKeys = {};

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
    if (failingDeleteKeys.contains(key)) {
      throw Exception('Hardware keystore failure deleting $key');
    }
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
  Future<http.Response> Function(
    Uri url,
    Map<String, String>? headers,
    Object? body,
  )? onDelete;

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

  @override
  Future<http.Response> delete(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    if (onDelete != null) return onDelete!(url, headers, body);
    return http.Response('{}', 200);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Phase 3 — Chunk 3.3: Networking, Router & Riverpod Controllers', () {
    test(
      'Test 1: SanctuaryHttpClient throws SanctuaryClientException on non-200 responses and passes authorization headers when session token exists',
      () async {
        final fakeStorage = TestSecureStorage();
        final sessionStorage = SecureSessionStorage(storage: fakeStorage);
        await sessionStorage.persistSession(
          accessToken: 'sanctuary-jwt-token-alpha',
          refreshToken: 'sanctuary-refresh-token-alpha',
          userId: 'user-uuid-1234',
          role: 'user',
        );

        final mockClient = FakeHttpClient();
        Map<String, String>? capturedHeaders;

        mockClient.onGet = (url, headers) async {
          capturedHeaders = headers;
          if (url.path == '/api/v1/auth/protected') {
            return http.Response(
              jsonEncode({'success': true, 'data': {'user': 'verified'}}),
              200,
            );
          } else if (url.path == '/api/v1/fail') {
            return http.Response(
              jsonEncode({
                'error_code': 'FORBIDDEN_ZONE',
                'message': 'Sanctuary chamber locked',
              }),
              403,
            );
          }
          return http.Response('Not Found', 404);
        };

        final client = SanctuaryHttpClient(sessionStorage, client: mockClient);

        // Verify successful authenticated GET request
        final successRes = await client.get('/api/v1/auth/protected');
        expect(successRes['success'], isTrue);
        expect(capturedHeaders, isNotNull);
        expect(
          capturedHeaders!['Authorization'],
          'Bearer sanctuary-jwt-token-alpha',
        );
        expect(capturedHeaders!['Content-Type'], 'application/json');
        expect(capturedHeaders!['Accept'], 'application/json');

        // Verify error translation to SanctuaryClientException on HTTP 403
        await expectLater(
          client.get('/api/v1/fail'),
          throwsA(
            isA<SanctuaryClientException>()
                .having((e) => e.statusCode, 'statusCode', 403)
                .having((e) => e.errorCode, 'errorCode', 'FORBIDDEN_ZONE')
                .having(
                  (e) => e.message,
                  'message',
                  'Sanctuary chamber locked',
                ),
          ),
        );
      },
    );

    testWidgets(
      'Test 2: goRouterProvider redirects unauthenticated sessions to /consent, and authenticated sessions to /main',
      (WidgetTester tester) async {
        // Sub-test 2A: Unauthenticated user accessing /main redirects to /consent
        final unauthContainer = ProviderContainer(
          overrides: [
            authStateProvider.overrideWith((ref) => Stream.value(false)),
          ],
        );
        addTearDown(unauthContainer.dispose);

        await tester.pumpWidget(
          UncontrolledProviderScope(
            container: unauthContainer,
            child: const UrHeartApp(),
          ),
        );
        await tester.pumpAndSettle();

        // Expect ConsentScreen to be rendered
        expect(find.text('ConsentScreen'), findsOneWidget);

        // Sub-test 2B: Authenticated user accessing auth route redirects to /main
        final authContainer = ProviderContainer(
          overrides: [
            authStateProvider.overrideWith((ref) => Stream.value(true)),
          ],
        );
        addTearDown(authContainer.dispose);

        await tester.pumpWidget(
          UncontrolledProviderScope(
            container: authContainer,
            child: const UrHeartApp(),
          ),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));

        // Expect SanctuaryNavigationShell to be rendered at /main
        expect(find.byType(SanctuaryNavigationShell), findsOneWidget);

        // Sub-test 2C: RBAC route guard (/admin/kyc-desk redirects non-admins to /main)
        final router = authContainer.read(goRouterProvider);
        router.go('/admin/kyc-desk');
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));

        // Non-admin user redirected back to /main (SanctuaryNavigationShell)
        expect(find.byType(SanctuaryNavigationShell), findsOneWidget);

        // When user is superadmin, kyc-desk is accessible
        authContainer.read(currentUserProvider.notifier).state =
            const CurrentUser(id: 'admin_1', role: 'superadmin');
        router.go('/admin/kyc-desk');
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expect(find.byType(SuperadminKycDeskScreen), findsOneWidget);
      },
    );

    test(
      'Test 3: GrowthHubController updates reward balance and accurately sets night slumber rest multipliers',
      () async {
        final fakeStorage = TestSecureStorage();
        final sessionStorage = SecureSessionStorage(storage: fakeStorage);
        final mockClient = FakeHttpClient();

        mockClient.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/ads/claim-reward') {
            return http.Response(
              jsonEncode({
                'success': true,
                'reward_type': 'quick_reflection',
                'credits_added': 10,
                'new_balance': 75,
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        };

        final sanctuaryClient =
            SanctuaryHttpClient(sessionStorage, client: mockClient);
        final billingService = SanctuaryBillingService(sanctuaryClient);
        final controller = GrowthHubController(billingService);

        expect(controller.state.rewardBalance, 0);
        expect(controller.state.restMultiplier, 1.0);
        expect(controller.state.isNightSlumberActive, isFalse);

        // Update Slumber multiplier to 1.75x
        controller.updateSlumberMultiplier(1.75);
        expect(controller.state.restMultiplier, 1.75);
        expect(controller.state.isNightSlumberActive, isTrue);

        // Update Slumber multiplier back to 1.0x (daytime)
        controller.updateSlumberMultiplier(1.0);
        expect(controller.state.restMultiplier, 1.0);
        expect(controller.state.isNightSlumberActive, isFalse);

        // Claim ad reward
        await controller.claimAdReward(
          transactionId: 'tx-mindful-777',
          adType: 'quick_reflection',
          network: 'admob',
        );
        expect(controller.state.rewardBalance, 75);
        expect(controller.state.isLoading, isFalse);
      },
    );

    test(
      'Test 4: BlindDateController initializes and flags isMilestoneLocked based on MAU response',
      () async {
        final fakeStorage = TestSecureStorage();
        final sessionStorage = SecureSessionStorage(storage: fakeStorage);
        final mockClient = FakeHttpClient();

        mockClient.onGet = (url, headers) async {
          if (url.path == '/api/v1/blind-date/eligibility') {
            return http.Response(
              jsonEncode({
                'status': 'milestone_locked',
                'current_mau': 42000,
                'target_mau': 1000000,
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        };

        mockClient.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/blind-date/queue/join') {
            return http.Response(
              jsonEncode({'success': true, 'queue_status': 'waiting'}),
              200,
            );
          }
          return http.Response('{}', 200);
        };

        final sanctuaryClient =
            SanctuaryHttpClient(sessionStorage, client: mockClient);
        final controller = BlindDateController(sanctuaryClient);

        // Await checkMilestoneStatus called in constructor
        await controller.checkMilestoneStatus();
        expect(controller.state.isMilestoneLocked, isTrue);
        expect(controller.state.currentMau, 42000);
        expect(controller.state.targetMau, 1000000);

        // Join queue
        await controller.joinQueue();
        expect(controller.state.queueStatus, 'waiting');
        expect(controller.state.isLoading, isFalse);
      },
    );

    test(
      'Test 5: VaultController correctly holds loaded grievances and nominee state',
      () async {
        final fakeStorage = TestSecureStorage();
        final sessionStorage = SecureSessionStorage(storage: fakeStorage);
        final mockClient = FakeHttpClient();

        mockClient.onGet = (url, headers) async {
          if (url.path == '/api/v1/vault/grievances' || url.path == '/api/v1/legal/grievances') {
            return http.Response(
              jsonEncode({
                'data': [
                  {
                    'id': 'grv-99',
                    'category': 'safety',
                    'status': 'under_review',
                  }
                ]
              }),
              200,
            );
          } else if (url.path == '/api/v1/vault/nominee' || url.path == '/api/v1/legal/nominee') {
            return http.Response(
              jsonEncode({
                'data': {
                  'full_name': 'Mira Ray',
                  'relationship': 'Sovereign Nominee',
                  'phone': '+919876543210',
                }
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        };

        final sanctuaryClient =
            SanctuaryHttpClient(sessionStorage, client: mockClient);
        final controller = VaultController(sanctuaryClient);

        await controller.loadVaultData();
        expect(controller.state.isLoading, isFalse);
        expect(controller.state.grievances.length, 1);
        expect(controller.state.grievances.first.referenceId, 'grv-99');
        expect(controller.state.nominee, isNotNull);
        expect(controller.state.nominee!.name, 'Mira Ray');
      },
    );

    test(
      'ResonancesController fetches incoming likes and mutual matches',
      () async {
        final fakeStorage = TestSecureStorage();
        final sessionStorage = SecureSessionStorage(storage: fakeStorage);
        final mockClient = FakeHttpClient();

        mockClient.onGet = (url, headers) async {
          if (url.path == '/api/v1/resonances/incoming') {
            return http.Response(
              jsonEncode({
                'data': [
                  {'user_id': 'peer-1', 'resonance_score': 94}
                ]
              }),
              200,
            );
          } else if (url.path == '/api/v1/resonances/mutual') {
            return http.Response(
              jsonEncode({
                'data': [
                  {'match_id': 'match-1', 'peer_id': 'peer-2'}
                ]
              }),
              200,
            );
          }
          return http.Response('{}', 200);
        };

        final sanctuaryClient =
            SanctuaryHttpClient(sessionStorage, client: mockClient);
        final controller = ResonancesController(sanctuaryClient);

        await controller.fetchResonances();
        expect(controller.state.isLoading, isFalse);
        expect(controller.state.incomingLikes.length, 1);
        expect(controller.state.incomingLikes.first['resonance_score'], 94);
        expect(controller.state.mutualMatches.length, 1);
        expect(controller.state.mutualMatches.first['match_id'], 'match-1');
      },
    );

    test('SanctuaryHttpClient throws 408 on request timeout', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final mockClient = FakeHttpClient();

      mockClient.onGet = (url, headers) async {
        await Future<void>.delayed(const Duration(milliseconds: 100));
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(
        sessionStorage,
        client: mockClient,
        requestTimeout: const Duration(milliseconds: 20),
      );

      await expectLater(
        client.get('/api/v1/slow'),
        throwsA(
          isA<SanctuaryClientException>()
              .having((e) => e.statusCode, 'statusCode', 408)
              .having((e) => e.errorCode, 'errorCode', 'REQUEST_TIMEOUT'),
        ),
      );
    });

    test('SanctuaryHttpClient coordinates concurrent 401 token refresh through single future', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      await sessionStorage.persistSession(
        accessToken: 'expired-access-token',
        refreshToken: 'valid-refresh-token',
        userId: 'u1',
        role: 'user',
      );

      int refreshCallCount = 0;
      final mockClient = FakeHttpClient();

      mockClient.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/auth/refresh') {
          refreshCallCount++;
          await Future<void>.delayed(const Duration(milliseconds: 30));
          return http.Response(
            jsonEncode({
              'success': true,
              'data': {'access_token': 'new-fresh-token'},
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      int getCallCount = 0;
      mockClient.onGet = (url, headers) async {
        getCallCount++;
        if (headers?['Authorization'] == 'Bearer expired-access-token') {
          return http.Response('{"error_code":"AUTH_EXPIRED"}', 401);
        }
        return http.Response('{"success": true}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: mockClient);

      // Launch 3 requests concurrently
      final f1 = client.get('/api/v1/data1');
      final f2 = client.get('/api/v1/data2');
      final f3 = client.get('/api/v1/data3');

      final results = await Future.wait([f1, f2, f3]);
      expect(results.length, 3);
      for (final r in results) {
        expect(r['success'], isTrue);
      }

      // Refresh was called exactly ONCE despite 3 concurrent 401 responses
      expect(refreshCallCount, 1);
      expect(getCallCount, 6);
      expect(await sessionStorage.readAuthToken(), 'new-fresh-token');
    });

    test('GrowthHubController preserves existing balance when new_balance is missing or nonnumeric', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final mockClient = FakeHttpClient();

      mockClient.onPost = (url, headers, body) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'reward_type': 'quick_reflection',
            // Missing new_balance
          }),
          200,
        );
      };

      final sanctuaryClient = SanctuaryHttpClient(sessionStorage, client: mockClient);
      final billingService = SanctuaryBillingService(sanctuaryClient);
      final controller = GrowthHubController(billingService);

      // Give initial non-zero balance
      controller.state = controller.state.copyWith(rewardBalance: 42);

      await controller.claimAdReward(
        transactionId: 'tx-missing-balance',
        adType: 'quick_reflection',
        network: 'admob',
      );

      // Should keep 42, not reset to 0
      expect(controller.state.rewardBalance, 42);
    });

    test('VaultController sets nominee to null when response envelope has data: null', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final mockClient = FakeHttpClient();

      mockClient.onGet = (url, headers) async {
        if (url.path == '/api/v1/vault/grievances' || url.path == '/api/v1/legal/grievances') {
          return http.Response('{"data": []}', 200);
        } else if (url.path == '/api/v1/vault/nominee' || url.path == '/api/v1/legal/nominee') {
          return http.Response('{"data": null}', 200);
        }
        return http.Response('{}', 200);
      };

      final sanctuaryClient = SanctuaryHttpClient(sessionStorage, client: mockClient);
      final controller = VaultController(sanctuaryClient);

      // Set pre-existing nominee
      controller.state = controller.state.copyWith(
        nominee: const NomineeModel(
          name: 'Previous Nominee',
          contact: '+919999999999',
          relationship: 'Sister',
        ),
      );

      await controller.loadVaultData();
      expect(controller.state.nominee, isNull);
    });

    test('SecureSessionStorage.clearSession preserves logged-in state and throws when auth token deletion fails', () async {
      final fakeStorage = TestSecureStorage();
      fakeStorage.failingDeleteKeys.add(SecureSessionStorage.keyAuthToken);
      final storage = SecureSessionStorage(storage: fakeStorage);
      addTearDown(storage.dispose);

      await storage.persistSession(
        accessToken: 'valid-jwt',
        refreshToken: 'valid-refresh',
        userId: 'usr-1',
        role: 'user',
      );

      final events = <bool>[];
      final sub = storage.watchAuthenticationState().listen(events.add);
      addTearDown(sub.cancel);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      expect(events, [true]);

      // Attempt clearSession which will fail to delete keyAuthToken
      expect(() => storage.clearSession(), throwsA(isA<Exception>()));

      await Future<void>.delayed(const Duration(milliseconds: 50));
      // Should NOT have emitted false!
      expect(events, [true]);

      // Verify auth token is still stored
      expect(await storage.readAuthToken(), 'valid-jwt');
    });

    test('SanctuaryHttpClient does not clear session when token refresh times out (408)', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      addTearDown(sessionStorage.dispose);

      await sessionStorage.persistSession(
        accessToken: 'expired-access-token',
        refreshToken: 'valid-refresh-token',
        userId: 'usr-1',
        role: 'user',
      );

      final mockClient = FakeHttpClient();
      mockClient.onGet = (url, headers) async {
        return http.Response('{"message": "Unauthorized"}', 401);
      };
      mockClient.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/auth/refresh') {
          throw const SanctuaryClientException(
            statusCode: 408,
            errorCode: 'REQUEST_TIMEOUT',
            message: 'Refresh request timed out',
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: mockClient);

      await expectLater(
        client.get('/api/v1/protected-data'),
        throwsA(
          isA<SanctuaryClientException>().having((e) => e.statusCode, 'statusCode', 408),
        ),
      );

      // Session MUST NOT be cleared on timeout!
      expect(await sessionStorage.readRefreshToken(), 'valid-refresh-token');
      expect(await sessionStorage.readAuthToken(), 'expired-access-token');
    });

    test('SanctuaryHttpClient clears session when token refresh is rejected with 401', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      addTearDown(sessionStorage.dispose);

      await sessionStorage.persistSession(
        accessToken: 'expired-access-token',
        refreshToken: 'invalid-refresh-token',
        userId: 'usr-1',
        role: 'user',
      );

      final mockClient = FakeHttpClient();
      mockClient.onGet = (url, headers) async {
        return http.Response('{"message": "Unauthorized"}', 401);
      };
      mockClient.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/auth/refresh') {
          return http.Response('{"error_code": "REFRESH_REVOKED", "message": "Refresh token revoked"}', 401);
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: mockClient);

      await expectLater(
        client.get('/api/v1/protected-data'),
        throwsA(
          isA<SanctuaryClientException>().having((e) => e.statusCode, 'statusCode', 401),
        ),
      );

      // Session MUST be cleared when refresh is rejected with 401
      expect(await sessionStorage.readRefreshToken(), isNull);
      expect(await sessionStorage.readAuthToken(), isNull);
    });

    testWidgets('UrHeartApp keeps protected routes closed while auth loads and redirects to /consent', (tester) async {
      final streamController = StreamController<bool>();
      addTearDown(streamController.close);

      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => streamController.stream),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const UrHeartApp(),
        ),
      );

      // While stream hasn't emitted, router defers and does NOT show SanctuaryNavigationShell
      expect(find.byType(SanctuaryNavigationShell), findsNothing);

      // Stream emits false (unauthenticated)
      streamController.add(false);
      await tester.pumpAndSettle();

      // Protected route is closed, user is routed to ConsentScreen
      expect(find.text('ConsentScreen'), findsOneWidget);
    });
  });
}
