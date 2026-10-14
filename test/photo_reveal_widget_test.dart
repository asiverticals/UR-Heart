import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/core/theme/widgets/glass_veil_widget.dart';
import 'package:ur_heart/features/feed/domain/models/discovery_profile.dart';
import 'package:ur_heart/features/profile/presentation/screens/seeker_profile_detail_screen.dart';

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
  String fullName = 'Devendra Dev',
  int age = 27,
  String locationName = 'Saket, Ayodhya',
  double? distanceKm = 1.2,
  String bio = 'Seeking timeless resonance and spiritual alignment.',
  String profession = 'Architect of Spaces',
  String education = 'Vedic Heritage School',
  int streakCount = 8,
  bool kycStatus = true,
  bool isPhotoVeiled = true,
}) {
  return DiscoveryProfile(
    id: id,
    fullName: fullName,
    age: age,
    gender: 'Man',
    interestedIn: 'Women',
    locationName: locationName,
    bio: bio,
    profession: profession,
    education: education,
    streakCount: streakCount,
    boostPoints: 120,
    kycStatus: kycStatus,
    isPhotoVeiled: isPhotoVeiled,
    photos: const ['https://media.urheart.app/users/devendra/slot_1.webp'],
    avatarUrl: 'https://media.urheart.app/users/devendra/avatar.webp',
    voiceSparkUrl: 'https://media.urheart.app/users/devendra/voice/spark.m4a',
    voiceSparkPrompt: 'What does your sanctuary feel like?',
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

  group('Phase 5 — Chunk 5.2: 35px Photo Blur Veil & Bilateral Photo Reveal Tests', () {
    testWidgets('Test 1: SeekerProfileDetailScreen renders GlassVeilWidget with 35px blur when isPhotoVeiled == true', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      const seekerId = '11111111-1111-1111-1111-111111111111';
      final profile = createTestProfile(id: seekerId, isPhotoVeiled: true);

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/revelation/photo/status/$seekerId') {
          return http.Response(
            jsonEncode({
              'data': {
                'target_id': seekerId,
                'status': 'veiled',
                'is_revealed': false,
              }
            }),
            200,
          );
        }
        if (url.path == '/api/v1/revelation/profile/$seekerId') {
          return http.Response(
            jsonEncode({
              'data': profile.toJson(),
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
          child: MaterialApp(
            home: SeekerProfileDetailScreen(
              userId: seekerId,
              initialProfile: profile,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Check Seeker Name & Details
      expect(find.text('Devendra Dev, 27'), findsOneWidget);
      expect(find.text('Architect of Spaces • Vedic Heritage School'), findsOneWidget);
      expect(find.text('Verified Seeker'), findsOneWidget);

      // Check 35px GlassVeilWidget is active with isVeiled == true
      final veilFinder = find.byType(GlassVeilWidget);
      expect(veilFinder, findsOneWidget);
      final veilWidget = tester.widget<GlassVeilWidget>(veilFinder);
      expect(veilWidget.isVeiled, isTrue);
      expect(veilWidget.veilBlur, equals(35.0));

      // Check Modesty Shield Banner
      expect(find.text('Veiled in Sacred Modesty'), findsWidgets);
      expect(find.text('Request Reveal'), findsOneWidget);
      expect(find.text('Instant Unveil (₹39)'), findsOneWidget);
    });

    testWidgets('Test 2: Tapping "Request Reveal" dispatches API request and updates UI to pending state', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      const seekerId = '11111111-1111-1111-1111-111111111111';
      final profile = createTestProfile(id: seekerId, isPhotoVeiled: true);
      bool requestSent = false;

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/revelation/photo/status/$seekerId') {
          return http.Response(
            jsonEncode({
              'data': {
                'target_id': seekerId,
                'status': requestSent ? 'pending' : 'veiled',
                'is_revealed': false,
              }
            }),
            200,
          );
        }
        if (url.path == '/api/v1/revelation/profile/$seekerId') {
          return http.Response(
            jsonEncode({
              'data': profile.toJson(),
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/revelation/photo/request') {
          requestSent = true;
          return http.Response(
            jsonEncode({
              'data': {
                'target_id': seekerId,
                'status': 'pending',
                'is_revealed': false,
                'message': 'Photo reveal request sent.',
              }
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
          child: MaterialApp(
            home: SeekerProfileDetailScreen(
              userId: seekerId,
              initialProfile: profile,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Tap Request Reveal
      await tester.tap(find.text('Request Reveal'));
      await tester.pumpAndSettle();

      expect(requestSent, isTrue);
      // Status banner updates to Pending
      expect(find.text('Reveal Request Pending'), findsOneWidget);
      expect(find.text('Request Sent'), findsOneWidget);
      expect(find.text('Awaiting gentle consent from seeker.'), findsOneWidget);
    });

    testWidgets('Test 3: Unveiled state (isPhotoVeiled == false) completely unmasks photos and removes modesty shield banner', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      const seekerId = '11111111-1111-1111-1111-111111111111';
      final profile = createTestProfile(id: seekerId, isPhotoVeiled: false);

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/revelation/photo/status/$seekerId') {
          return http.Response(
            jsonEncode({
              'data': {
                'target_id': seekerId,
                'status': 'accepted',
                'is_revealed': true,
              }
            }),
            200,
          );
        }
        if (url.path == '/api/v1/revelation/profile/$seekerId') {
          return http.Response(
            jsonEncode({
              'data': profile.toJson(),
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
          child: MaterialApp(
            home: SeekerProfileDetailScreen(
              userId: seekerId,
              initialProfile: profile,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // GlassVeilWidget is present with isVeiled == false
      final veilFinder = find.byType(GlassVeilWidget);
      expect(veilFinder, findsOneWidget);
      final veilWidget = tester.widget<GlassVeilWidget>(veilFinder);
      expect(veilWidget.isVeiled, isFalse);

      // Modesty shield banner is NOT present
      expect(find.text('Veiled in Sacred Modesty'), findsNothing);
      expect(find.text('Request Reveal'), findsNothing);
      expect(find.text('Instant Unveil (₹39)'), findsNothing);
    });

    testWidgets('Test 4: Instant Unveil (₹39) micro-perk triggers checkout and unveils photos', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      const seekerId = '11111111-1111-1111-1111-111111111111';
      final profile = createTestProfile(id: seekerId, isPhotoVeiled: true);
      bool unlockInvoked = false;

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/revelation/photo/status/$seekerId') {
          return http.Response(
            jsonEncode({
              'data': {
                'target_id': seekerId,
                'status': unlockInvoked ? 'purchased_unlock' : 'veiled',
                'is_revealed': unlockInvoked,
              }
            }),
            200,
          );
        }
        if (url.path == '/api/v1/revelation/profile/$seekerId') {
          return http.Response(
            jsonEncode({
              'data': profile.toJson(),
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/revelation/photo/unlock-perk') {
          unlockInvoked = true;
          return http.Response(
            jsonEncode({
              'data': {
                'target_id': seekerId,
                'status': 'purchased_unlock',
                'is_revealed': true,
                'message': 'Veil unmasked via Sacred Micro-Perk.',
              }
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
          child: MaterialApp(
            home: SeekerProfileDetailScreen(
              userId: seekerId,
              initialProfile: profile,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Tap Instant Unveil
      await tester.tap(find.text('Instant Unveil (₹39)'));
      await tester.pumpAndSettle();

      expect(unlockInvoked, isTrue);

      // Photos unmasked and banner dismissed
      final veilWidget = tester.widget<GlassVeilWidget>(find.byType(GlassVeilWidget));
      expect(veilWidget.isVeiled, isFalse);
      expect(find.text('Veiled in Sacred Modesty'), findsNothing);
    });

    testWidgets('Test 5: 7-Second Voice Spark waveform player toggles playback and progress', (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());
      addTearDown(() => tester.view.resetDevicePixelRatio());

      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      const seekerId = '11111111-1111-1111-1111-111111111111';
      final profile = createTestProfile(id: seekerId);

      fakeHttp.onGet = (url, headers) async {
        if (url.path == '/api/v1/revelation/photo/status/$seekerId') {
          return http.Response(
            jsonEncode({
              'data': {
                'target_id': seekerId,
                'status': 'veiled',
                'is_revealed': false,
              }
            }),
            200,
          );
        }
        if (url.path == '/api/v1/revelation/profile/$seekerId') {
          return http.Response(
            jsonEncode({
              'data': profile.toJson(),
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
          child: MaterialApp(
            home: SeekerProfileDetailScreen(
              userId: seekerId,
              initialProfile: profile,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('7-Second Voice Spark'), findsOneWidget);
      expect(find.text('What does your sanctuary feel like?'), findsOneWidget);
      expect(find.byIcon(Icons.play_arrow_rounded), findsOneWidget);

      // Tap Play
      await tester.tap(find.byIcon(Icons.play_arrow_rounded));
      await tester.pump(const Duration(milliseconds: 300));

      expect(find.byIcon(Icons.stop_rounded), findsOneWidget);
      expect(find.text('Playing 7.0s authentic voice spark...'), findsOneWidget);

      // Tap Stop
      await tester.tap(find.byIcon(Icons.stop_rounded));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.play_arrow_rounded), findsOneWidget);
    });
  });
}
