import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/feed/domain/models/discovery_profile.dart';
import 'package:ur_heart/features/feed/presentation/controllers/feed_controller.dart';
import 'package:ur_heart/features/feed/presentation/screens/feed_screen.dart';

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
}

class FakeHttpClient extends Fake implements http.Client {
  Future<http.Response> Function(Uri url, Map<String, String>? headers)? onGet;
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onPost;

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
  void close() {}
}

DiscoveryProfile createTestProfile({
  String id = '11111111-1111-1111-1111-111111111111',
  String fullName = 'Radha Raman',
  int age = 24,
  String locationName = 'Saket, Ayodhya',
  double? distanceKm = 1.1,
  String bio = 'Walking the path of sincere kinship.',
  String profession = 'Architect',
  String education = 'Gurukul Vishwavidyalaya',
  int streakCount = 5,
  bool kycStatus = true,
  bool isPhotoVeiled = true,
}) {
  return DiscoveryProfile(
    id: id,
    fullName: fullName,
    age: age,
    gender: 'Woman',
    interestedIn: 'Men',
    locationName: locationName,
    bio: bio,
    profession: profession,
    education: education,
    streakCount: streakCount,
    boostPoints: 100,
    kycStatus: kycStatus,
    isPhotoVeiled: isPhotoVeiled,
    photos: const ['https://media.urheart.app/users/radha/slot_1.webp'],
    avatarUrl: 'https://media.urheart.app/users/radha/avatar.webp',
    voiceSparkUrl: 'https://media.urheart.app/users/radha/voice/spark.m4a',
    voiceSparkPrompt: 'What brings you peace?',
    voiceSparkDuration: 7.0,
    isVoiceVerified: true,
    distanceKm: distanceKm,
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Phase 5 — Chunk 5.1: Feed Deck & Quota Widget Tests', () {
    testWidgets('Test 1: FeedScreen renders quota indicator and profile card with fuzzed distance chip', (tester) async {
      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/feed') {
          return http.Response(
            jsonEncode({
              'profiles': [
                createTestProfile().toJson(),
              ],
              'swipes_remaining': 10,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sanctuaryHttpClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(
            home: FeedScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Check Mindful Quota Pill
      expect(find.text('Swipes Remaining: 10/10'), findsOneWidget);
      expect(find.text('5d'), findsOneWidget); // Streak counter badge

      // Check Profile Card & Details
      expect(find.text('Radha Raman, 24'), findsOneWidget);
      expect(find.text('Architect • Gurukul Vishwavidyalaya'), findsOneWidget);
      expect(find.text('Walking the path of sincere kinship.'), findsOneWidget);

      // Check DPDP Fuzzed Distance Chip
      expect(find.text('Saket, Ayodhya • ~1.1 km away'), findsOneWidget);

      // Check Voice Spark Button
      expect(find.text('What brings you peace? (7s)'), findsOneWidget);

      // Check Action Deck Controls
      expect(find.byTooltip('Pass with Grace'), findsOneWidget);
      expect(find.byTooltip('Direct Letter'), findsOneWidget);
      expect(find.byTooltip('Resonate'), findsOneWidget);
    });

    testWidgets('Test 2: Triggering pass/like actions removes card and decrements swipe quota', (tester) async {
      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      final profile1 = createTestProfile(id: 'p1', fullName: 'First Seeker');
      final profile2 = createTestProfile(id: 'p2', fullName: 'Second Seeker');

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/feed') {
          return http.Response(
            jsonEncode({
              'profiles': [profile1.toJson(), profile2.toJson()],
              'swipes_remaining': 10,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      String? recordedAction;
      String? recordedTarget;

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/feed/swipe') {
          final parsed = jsonDecode(body.toString());
          recordedAction = parsed['action'];
          recordedTarget = parsed['target_id'];
          return http.Response(
            jsonEncode({
              'is_match': false,
              'match_id': null,
              'swipes_remaining': 9,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sanctuaryHttpClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(
            home: FeedScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('First Seeker, 24'), findsOneWidget);

      // Tap Pass button
      await tester.tap(find.byTooltip('Pass with Grace'));
      await tester.pumpAndSettle();

      expect(recordedAction, 'pass');
      expect(recordedTarget, 'p1');

      // Top card should now be Second Seeker
      expect(find.text('Second Seeker, 24'), findsOneWidget);
      expect(find.text('Swipes Remaining: 9/10'), findsOneWidget);
    });

    testWidgets('Test 3: Empty deck or exhausted quota renders mindful message', (tester) async {
      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/feed') {
          return http.Response(
            jsonEncode({
              'profiles': [],
              'swipes_remaining': 0,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sanctuaryHttpClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(
            home: FeedScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text("You have met today's rhythm."), findsOneWidget);
      expect(
        find.text(
          "Return tomorrow or complete a mindful reflection in the Growth Hub.",
        ),
        findsOneWidget,
      );
      expect(find.text('Swipes Remaining: 0/10'), findsOneWidget);
    });

    testWidgets('Test 4: Mutual resonance triggers Divine Resonance modal alert', (tester) async {
      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      final profile = createTestProfile(id: 'target-match', fullName: 'Soul Sister');

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/feed') {
          return http.Response(
            jsonEncode({
              'profiles': [profile.toJson()],
              'swipes_remaining': 5,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/feed/swipe') {
          return http.Response(
            jsonEncode({
              'is_match': true,
              'match_id': 'match-uuid-999',
              'swipes_remaining': 4,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sanctuaryHttpClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(
            home: FeedScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Tap Resonate button
      await tester.tap(find.byTooltip('Resonate'));
      await tester.pumpAndSettle();

      // Verify Mutual Match Dialog
      expect(find.text('Divine Resonance Ignited'), findsOneWidget);
      expect(
        find.textContaining('A sacred contact reveal token has been provisioned.'),
        findsOneWidget,
      );
      expect(find.text('Continue In Sanctuary'), findsOneWidget);

      // Dismiss dialog
      await tester.tap(find.text('Continue In Sanctuary'));
      await tester.pumpAndSettle();

      expect(find.text('Divine Resonance Ignited'), findsNothing);
    });

    testWidgets('Test 5: Direct Letter modal opens, inputs text, and dispatches like with letter', (tester) async {
      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      final profile = createTestProfile(id: 'target-letter', fullName: 'Devi');

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/feed') {
          return http.Response(
            jsonEncode({
              'profiles': [profile.toJson()],
              'swipes_remaining': 8,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      String? letterSent;
      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/feed/swipe') {
          final parsed = jsonDecode(body.toString());
          letterSent = parsed['direct_letter_text'];
          return http.Response(
            jsonEncode({
              'is_match': false,
              'match_id': null,
              'swipes_remaining': 7,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sanctuaryHttpClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(
            home: FeedScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Tap Direct Letter button
      await tester.tap(find.byTooltip('Direct Letter'));
      await tester.pumpAndSettle();

      expect(find.text('Direct Letter with Grace'), findsOneWidget);
      expect(find.textContaining('Compose a thoughtful note to Devi.'), findsOneWidget);

      // Enter letter note
      await tester.enterText(
        find.byType(TextField),
        'Your poetry in the bio resonated deeply with me.',
      );
      await tester.pumpAndSettle();

      // Tap Send & Resonate
      await tester.tap(find.text('Send & Resonate'));
      await tester.pumpAndSettle();

      expect(letterSent, 'Your poetry in the bio resonated deeply with me.');
      expect(find.text('Direct Letter with Grace'), findsNothing);
    });

    testWidgets('Test 6: Non-quota 403 error rolls back profile card and does not exhaust quota', (tester) async {
      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      final profile = createTestProfile(id: 'blocked-seeker', fullName: 'Blocked Seeker');

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/feed') {
          return http.Response(
            jsonEncode({
              'profiles': [profile.toJson()],
              'swipes_remaining': 7,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/feed/swipe') {
          return http.Response(
            jsonEncode({
              'error_code': 'SEEKER_BLOCKED',
              'message': 'Cannot interact with a blocked seeker profile.',
            }),
            403,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sanctuaryHttpClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(
            home: FeedScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Blocked Seeker, 24'), findsOneWidget);
      expect(find.text('Swipes Remaining: 7/10'), findsOneWidget);

      // Attempt to resonate
      await tester.tap(find.byTooltip('Resonate'));
      await tester.pumpAndSettle();

      // Card must be restored (not discarded)
      expect(find.text('Blocked Seeker, 24'), findsOneWidget);
      // Quota must NOT be 0 (it should remain 7)
      expect(find.text('Swipes Remaining: 7/10'), findsOneWidget);
      // Error message should be displayed
      expect(find.text('Cannot interact with a blocked seeker profile.'), findsOneWidget);
    });

    testWidgets('Test 7: Distance chip displays only locationName when distanceKm is null', (tester) async {
      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/feed') {
          return http.Response(
            jsonEncode({
              'profiles': [
                createTestProfile(
                  locationName: 'Varanasi Ghats',
                  distanceKm: null,
                ).toJson(),
              ],
              'swipes_remaining': 10,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sanctuaryHttpClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(
            home: FeedScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Varanasi Ghats'), findsOneWidget);
      expect(find.textContaining('km away'), findsNothing);
    });

    testWidgets('Test 8: Empty deck renders errorMessage and Retry button when deck load fails', (tester) async {
      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/feed') {
          return http.Response(
            jsonEncode({
              'error_code': 'DAILY_SWIPE_QUOTA_EXHAUSTED',
              'message': "You have met today's rhythm. Return tomorrow or complete a mindful reflection.",
            }),
            403,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sanctuaryHttpClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(
            home: FeedScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Discovery Paused'), findsOneWidget);
      expect(find.text("You have met today's rhythm. Return tomorrow or complete a mindful reflection."), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('Test 9: Action buttons are disabled while isSwiping is active', (tester) async {
      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/feed') {
          return http.Response(
            jsonEncode({
              'profiles': [
                createTestProfile().toJson(),
              ],
              'swipes_remaining': 10,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sanctuaryHttpClientProvider.overrideWithValue(client),
          ],
          child: const MaterialApp(
            home: FeedScreen(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      final element = tester.element(find.byType(FeedScreen));
      final container = ProviderScope.containerOf(element);
      container.read(feedControllerProvider.notifier).state =
          container.read(feedControllerProvider).copyWith(isSwiping: true);
      await tester.pump();

      // Tap Resonate while swiping - should be ignored
      await tester.tap(find.byTooltip('Resonate'));
      await tester.pump();

      // State is still swiping, card not removed by second tap
      expect(find.text('Radha Raman, 24'), findsOneWidget);
    });
  });
}

