import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:ur_heart/core/app/app_router.dart';
import 'package:ur_heart/core/app/ur_heart_app.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/services/notification_service.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/feed/domain/models/discovery_profile.dart';
import 'package:ur_heart/features/profile/presentation/screens/seeker_profile_detail_screen.dart';

class MockSecureStorage extends Fake implements FlutterSecureStorage {
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
}

class AdversarialFakeHttpClient extends http.BaseClient {
  Future<http.Response> Function(http.Request request)? handler;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (request is http.Request && handler != null) {
      final response = await handler!(request);
      return http.StreamedResponse(
        Stream.value(utf8.encode(response.body)),
        response.statusCode,
        headers: response.headers,
      );
    }
    return http.StreamedResponse(
      Stream.value(utf8.encode('{}')),
      200,
      headers: {'content-type': 'application/json'},
    );
  }
}

class FaultInjectingNotificationService extends NotificationService {
  int initializeCalls = 0;
  bool shouldThrowSynchronously = false;
  bool shouldThrowAsynchronously = false;

  FaultInjectingNotificationService(super.client);

  @override
  Future<bool> initialize({String? fcmToken, String? installationId}) async {
    initializeCalls++;
    if (shouldThrowSynchronously) {
      throw StateError('Simulated unexpected synchronous crash in initialize');
    }
    if (shouldThrowAsynchronously) {
      await Future<void>.delayed(const Duration(milliseconds: 10));
      throw const SocketException('Simulated asynchronous socket failure');
    }
    return super.initialize(fcmToken: fcmToken, installationId: installationId);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const testDiscoveryProfile = DiscoveryProfile(
    id: 'profile-uuid-001',
    fullName: 'Ananya Deshmukh',
    age: 26,
    gender: 'Woman',
    interestedIn: 'Man',
    locationName: 'Indiranagar, Bengaluru',
    bio: 'Mindful architecture and quiet mornings.',
    profession: 'Architect',
    education: 'CEPT University',
    streakCount: 12,
    boostPoints: 45,
    kycStatus: true,
    isPhotoVeiled: true,
    photos: ['https://example.com/photo1.jpg'],
  );

  group('Adversarial Dimension 1: /seeker-detail Routing Stress Tests', () {
    testWidgets('1.1: Missing query string and null extra resolves to empty string without exception', (tester) async {
      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => Stream.value(true)),
        ],
      );
      addTearDown(container.dispose);

      final router = container.read(goRouterProvider);
      router.go('/seeker-detail');

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      final detailFinder = find.byType(SeekerProfileDetailScreen);
      expect(detailFinder, findsOneWidget);
      final widget = tester.widget<SeekerProfileDetailScreen>(detailFinder);
      expect(widget.userId, isEmpty);
      expect(widget.initialProfile, isNull);
    });

    testWidgets('1.2: Empty query parameters (?userId= and ?user_id=) fallback gracefully to empty string', (tester) async {
      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => Stream.value(true)),
        ],
      );
      addTearDown(container.dispose);

      final router = container.read(goRouterProvider);

      // Case A: ?userId=
      router.go('/seeker-detail?userId=');
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      var widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, isEmpty);

      // Case B: ?user_id=
      router.go('/seeker-detail?user_id=');
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, isEmpty);
    });

    testWidgets('1.3: Non-UUID query parameters and URL-encoded special characters are safely parsed without exception', (tester) async {
      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => Stream.value(true)),
        ],
      );
      addTearDown(container.dispose);

      final router = container.read(goRouterProvider);

      // 1.3A: Non-UUID alphanumeric with punctuation
      router.go('/seeker-detail?userId=non-uuid-seeker-alpha-numeric_123');
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      var widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, 'non-uuid-seeker-alpha-numeric_123');

      // 1.3B: URL-encoded special characters (including #, &, $, spaces)
      final encodedUrl = Uri(
        path: '/seeker-detail',
        queryParameters: {'userId': 'seeker #1 (special & critical) \$99'},
      ).toString();
      router.go(encodedUrl);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, 'seeker #1 (special & critical) \$99');

      // 1.3C: Raw unencoded '#' acts as URI fragment delimiter per RFC 3986 without throwing
      router.go('/seeker-detail?userId=raw-prefix#fragment-part');
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, 'raw-prefix');
    });

    testWidgets('1.4: Unexpected extra types (int, String, List, bool, DateTime) do not trigger cast exceptions', (tester) async {
      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => Stream.value(true)),
        ],
      );
      addTearDown(container.dispose);

      final router = container.read(goRouterProvider);

      final hostileExtras = [
        42,
        'unexpected_string_token',
        ['item1', 'item2', 999],
        true,
        DateTime(2026, 10, 16),
      ];

      for (final extra in hostileExtras) {
        router.go('/seeker-detail', extra: extra);
        await tester.pumpWidget(
          UncontrolledProviderScope(
            container: container,
            child: MaterialApp.router(routerConfig: router),
          ),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));

        final widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
        expect(widget.userId, isEmpty, reason: 'Extra $extra should fallback to empty string userId');
        expect(widget.initialProfile, isNull);
      }
    });

    testWidgets('1.5: Edge-case Maps in extra are defensively parsed', (tester) async {
      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => Stream.value(true)),
        ],
      );
      addTearDown(container.dispose);

      final router = container.read(goRouterProvider);

      // Empty Map
      router.go('/seeker-detail', extra: <String, dynamic>{});
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      var widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, isEmpty);

      // Map with null userId
      router.go('/seeker-detail', extra: {'userId': null});
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, isEmpty);

      // Map with numeric userId: verifies ?.toString() prevents TypeError
      router.go('/seeker-detail', extra: {'userId': 123456789});
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, '123456789');

      // Map with snake_case user_id
      router.go('/seeker-detail', extra: {'user_id': 'snake-uuid-777'});
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, 'snake-uuid-777');

      // Map with seeker_id
      router.go('/seeker-detail', extra: {'seeker_id': 'seeker-uuid-888'});
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, 'seeker-uuid-888');

      // Non-string-keyed Map
      router.go('/seeker-detail', extra: <int, dynamic>{100: 'val'});
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, isEmpty);
    });

    testWidgets('1.6: Precedence: query param overrides Map extra and DiscoveryProfile.id', (tester) async {
      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => Stream.value(true)),
        ],
      );
      addTearDown(container.dispose);

      final router = container.read(goRouterProvider);

      // Query param + Map extra
      router.go('/seeker-detail?userId=query-wins-1', extra: {'userId': 'map-loses'});
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      var widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, 'query-wins-1');

      // Query param + DiscoveryProfile: query param takes precedence for userId, while initialProfile is retained
      router.go('/seeker-detail?userId=query-wins-2', extra: testDiscoveryProfile);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      widget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(widget.userId, 'query-wins-2');
      expect(widget.initialProfile, equals(testDiscoveryProfile));
    });

    testWidgets('1.7: Deep push and pop navigation stack operates cleanly without exceptions', (tester) async {
      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => Stream.value(true)),
        ],
      );
      addTearDown(container.dispose);

      final router = container.read(goRouterProvider);
      router.go('/main');

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      // Push to /seeker-detail with query param and extra profile
      router.push('/seeker-detail?userId=${testDiscoveryProfile.id}', extra: testDiscoveryProfile);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.byType(SeekerProfileDetailScreen), findsOneWidget);
      final detailWidget = tester.widget<SeekerProfileDetailScreen>(find.byType(SeekerProfileDetailScreen));
      expect(detailWidget.userId, testDiscoveryProfile.id);

      // Pop back to /main and allow full route transition (500ms) to settle
      router.pop();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.byType(SeekerProfileDetailScreen), findsNothing);
    });
  });

  group('Adversarial Dimension 2: NotificationService.initialize() Stress Tests', () {
    late AdversarialFakeHttpClient fakeHttp;
    late SecureSessionStorage sessionStorage;
    late SanctuaryHttpClient sanctuaryClient;
    late NotificationService service;

    setUp(() {
      fakeHttp = AdversarialFakeHttpClient();
      final mockStorage = MockSecureStorage();
      sessionStorage = SecureSessionStorage(storage: mockStorage);
      sanctuaryClient = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      service = NotificationService(sanctuaryClient);
    });

    test('2.1: null or empty fcmToken marks service initialized and skips HTTP dispatch', () async {
      int requestCount = 0;
      fakeHttp.handler = (req) async {
        requestCount++;
        return http.Response('{}', 200);
      };

      // Case A: null token
      expect(service.isInitialized, isFalse);
      final nullResult = await service.initialize(fcmToken: null);
      expect(nullResult, isTrue);
      expect(service.isInitialized, isTrue);
      expect(requestCount, 0);

      // Case B: empty token
      final emptyResult = await service.initialize(fcmToken: '');
      expect(emptyResult, isTrue);
      expect(service.isInitialized, isTrue);
      expect(requestCount, 0);
    });

    test('2.2: Simulated SocketException (network offline) returns false and does not throw', () async {
      fakeHttp.handler = (req) async {
        throw const SocketException("Failed host lookup: 'urheart.app'");
      };

      expect(service.isInitialized, isFalse);
      final result = await service.initialize(fcmToken: 'valid_token_xyz');

      expect(result, isFalse);
      expect(service.isInitialized, isTrue);
    });

    test('2.3: Simulated TimeoutException returns false and does not throw', () async {
      fakeHttp.handler = (req) async {
        throw TimeoutException('Request timed out after 15s');
      };

      final result = await service.initialize(fcmToken: 'valid_token_xyz');
      expect(result, isFalse);
      expect(service.isInitialized, isTrue);
    });

    test('2.4: Simulated HTTP 500 Internal Server Error returns false and does not throw', () async {
      fakeHttp.handler = (req) async {
        return http.Response(
          jsonEncode({'error': 'Internal server error'}),
          500,
          headers: {'content-type': 'application/json'},
        );
      };

      final result = await service.initialize(fcmToken: 'valid_token_xyz');
      expect(result, isFalse);
      expect(service.isInitialized, isTrue);
    });

    test('2.5: Simulated HTTP 401 Unauthorized returns false and does not throw', () async {
      fakeHttp.handler = (req) async {
        return http.Response(
          jsonEncode({'detail': 'Could not validate credentials'}),
          401,
          headers: {'content-type': 'application/json'},
        );
      };

      final result = await service.initialize(fcmToken: 'valid_token_xyz');
      expect(result, isFalse);
      expect(service.isInitialized, isTrue);
    });

    test('2.6: Malformed response body returns false without unhandled exceptions', () async {
      // Body returns invalid non-boolean registered or corrupted envelope
      fakeHttp.handler = (req) async {
        return http.Response(
          jsonEncode({'data': {'registered': 'unexpected_string'}}),
          200,
          headers: {'content-type': 'application/json'},
        );
      };

      final result = await service.initialize(fcmToken: 'valid_token_xyz');
      expect(result, isFalse);
      expect(service.isInitialized, isTrue);
    });
  });

  group('Adversarial Dimension 3: UrHeartApp Session Wiring & Resilience Stress Tests', () {
    testWidgets('3.1: Synchronous exception in notification initialize does not crash UrHeartApp widget tree', (tester) async {
      final mockStorage = MockSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: mockStorage);
      final fakeHttp = AdversarialFakeHttpClient();
      final sanctuaryClient = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      final faultService = FaultInjectingNotificationService(sanctuaryClient)
        ..shouldThrowSynchronously = true;

      final authStreamController = StreamController<bool>.broadcast();

      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => authStreamController.stream),
          notificationServiceProvider.overrideWithValue(faultService),
        ],
      );
      addTearDown(container.dispose);
      addTearDown(authStreamController.close);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const UrHeartApp(),
        ),
      );
      await tester.pump();

      // Trigger auth transition to true: faultService throws synchronously
      authStreamController.add(true);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(faultService.initializeCalls, 1);
      // App continues running, MaterialApp.router is intact
      expect(find.byType(MaterialApp), findsOneWidget);
    });

    testWidgets('3.2: Asynchronous exception in notification initialize is caught by .catchError without unhandled async failure', (tester) async {
      final mockStorage = MockSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: mockStorage);
      final fakeHttp = AdversarialFakeHttpClient();
      final sanctuaryClient = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      final faultService = FaultInjectingNotificationService(sanctuaryClient)
        ..shouldThrowAsynchronously = true;

      final authStreamController = StreamController<bool>.broadcast();

      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => authStreamController.stream),
          notificationServiceProvider.overrideWithValue(faultService),
        ],
      );
      addTearDown(container.dispose);
      addTearDown(authStreamController.close);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const UrHeartApp(),
        ),
      );
      await tester.pump();

      // Transition auth to true: triggers async failure caught by catchError((_) => false)
      authStreamController.add(true);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(faultService.initializeCalls, 1);
      expect(find.byType(MaterialApp), findsOneWidget);
    });

    testWidgets('3.3: Rapid flappy auth transitions [false, true, false, true, true, false, true] dispatch initialize strictly on rising edges', (tester) async {
      final mockStorage = MockSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: mockStorage);
      final fakeHttp = AdversarialFakeHttpClient();
      final sanctuaryClient = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      final testService = FaultInjectingNotificationService(sanctuaryClient);
      final authStreamController = StreamController<bool>.broadcast();

      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => authStreamController.stream),
          notificationServiceProvider.overrideWithValue(testService),
        ],
      );
      addTearDown(container.dispose);
      addTearDown(authStreamController.close);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const UrHeartApp(),
        ),
      );
      await tester.pump();

      // 1. Initial false -> 0 calls
      authStreamController.add(false);
      await tester.pump();
      expect(testService.initializeCalls, 0);

      // 2. Transition false -> true: Rising edge #1 -> 1 call
      authStreamController.add(true);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 20));
      expect(testService.initializeCalls, 1);

      // 3. Transition true -> false -> still 1 call
      authStreamController.add(false);
      await tester.pump();
      expect(testService.initializeCalls, 1);

      // 4. Transition false -> true: Rising edge #2 -> 2 calls
      authStreamController.add(true);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 20));
      expect(testService.initializeCalls, 2);

      // 5. Consecutive true -> true: suppressed by transition filter -> still 2 calls
      authStreamController.add(true);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 20));
      expect(testService.initializeCalls, 2);

      // 6. Transition true -> false -> still 2 calls
      authStreamController.add(false);
      await tester.pump();
      expect(testService.initializeCalls, 2);

      // 7. Transition false -> true: Rising edge #3 -> 3 calls
      authStreamController.add(true);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 20));
      expect(testService.initializeCalls, 3);
    });

    testWidgets('3.4: Cold boot authenticated stream (AsyncLoading -> AsyncData(true)) correctly triggers initialize once', (tester) async {
      final mockStorage = MockSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: mockStorage);
      final fakeHttp = AdversarialFakeHttpClient();
      final sanctuaryClient = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      final testService = FaultInjectingNotificationService(sanctuaryClient);

      // Simulates cold boot: StreamProvider emits AsyncLoading initially then AsyncData(true)
      final authStreamController = StreamController<bool>();

      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => authStreamController.stream),
          notificationServiceProvider.overrideWithValue(testService),
        ],
      );
      addTearDown(container.dispose);
      addTearDown(authStreamController.close);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const UrHeartApp(),
        ),
      );
      await tester.pump();

      // Cold boot emission
      authStreamController.add(true);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(testService.initializeCalls, 1);
    });
  });
}
