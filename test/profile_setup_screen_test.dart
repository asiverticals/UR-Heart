import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/profile_setup/presentation/controllers/profile_setup_controller.dart';
import 'package:ur_heart/features/profile_setup/presentation/screens/profile_setup_screen.dart';
import 'package:ur_heart/features/profile_setup/presentation/widgets/photo_slot_grid.dart';
import 'package:ur_heart/features/profile_setup/presentation/widgets/voice_spark_recorder_widget.dart';

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
}

class FakeHttpClient extends Fake implements http.Client {
  Future<http.Response> Function(Uri url, Map<String, String>? headers)? onGet;
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onPost;
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onPut;
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onDelete;

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
  Future<http.Response> put(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    if (onPut != null) return onPut!(url, headers, body);
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

  @override
  void close() {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Phase 4 — Chunk 4.2: ProfileSetupScreen & R2 Pipeline Tests', () {
    testWidgets('Test 1: PhotoSlotGrid displays exactly 5 slots with primary avatar hero badge', (tester) async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();
      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileSetupControllerProvider.overrideWith((ref) => controller),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: PhotoSlotGrid(),
              ),
            ),
          ),
        ),
      );

      expect(find.text('Sacred Moments (5 Slots)'), findsOneWidget);
      expect(find.text('0/5 Uploaded'), findsOneWidget);
      expect(find.text('Primary Avatar'), findsOneWidget);
      expect(find.text('Slot 1 — Primary Avatar'), findsOneWidget);
      expect(find.text('Slot 2'), findsOneWidget);
      expect(find.text('Slot 3'), findsOneWidget);
      expect(find.text('Slot 4'), findsOneWidget);
      expect(find.text('Slot 5'), findsOneWidget);
    });

    test('Test 2: ProfileSetupController.uploadPhotoSlot requests presigned URL and PUTs binary to R2', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      Uri? presignedRequestedUrl;
      String? presignedRequestBody;
      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/media/presigned-url') {
          presignedRequestedUrl = url;
          presignedRequestBody = body?.toString();
          return http.Response(
            jsonEncode({
              'success': true,
              'upload_url': 'https://r2.cloudflare.com/presigned-upload-slot-1',
              'public_cdn_url': 'https://media.urheart.app/users/test/moments/slot_1.webp',
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      Uri? r2PutUrl;
      List<int>? r2PutBody;
      String? r2ContentType;
      fakeHttp.onPut = (url, headers, body) async {
        r2PutUrl = url;
        r2ContentType = headers?['Content-Type'];
        if (body is List<int>) {
          r2PutBody = body;
        }
        return http.Response('', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      final sampleWebpBytes = [0x52, 0x49, 0x46, 0x46, 0x00, 0x00, 0x00, 0x00];
      final success = await controller.uploadPhotoSlot(1, sampleWebpBytes);

      expect(success, isTrue);
      expect(presignedRequestedUrl?.path, '/api/v1/media/presigned-url');
      expect(presignedRequestBody, contains('slot_number'));
      expect(r2PutUrl?.toString(), 'https://r2.cloudflare.com/presigned-upload-slot-1');
      expect(r2ContentType, 'image/webp');
      expect(r2PutBody, sampleWebpBytes);
      expect(controller.state.photoUrls[0], 'https://media.urheart.app/users/test/moments/slot_1.webp');
      expect(controller.state.avatarUrl, 'https://media.urheart.app/users/test/moments/slot_1.webp');
      expect(controller.state.isUploadingMedia, isFalse);
    });

    test('Test 3: Submitting profile fails if required fields are missing', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();
      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      // 1. Missing name
      var ok = await controller.submitProfile();
      expect(ok, isFalse);
      expect(controller.state.errorMessage, contains('full name'));

      // 2. Set name, but missing photos
      controller.updateTextFields(fullName: 'Aarav Patel');
      ok = await controller.submitProfile();
      expect(ok, isFalse);
      expect(controller.state.errorMessage, contains('at least 1 photo'));

      // 3. Set photo, but missing contact bridge handle
      fakeHttp.onPost = (url, headers, body) async {
        return http.Response(
          jsonEncode({
            'upload_url': 'https://r2.cloudflare.com/slot-1',
            'public_cdn_url': 'https://media.urheart.app/slot_1.webp',
          }),
          200,
        );
      };
      fakeHttp.onPut = (url, headers, body) async => http.Response('', 200);

      await controller.uploadPhotoSlot(1, [1, 2, 3]);
      ok = await controller.submitProfile();
      expect(ok, isFalse);
      expect(controller.state.errorMessage, contains('contact bridge'));
    });

    testWidgets('Test 4: VoiceSparkRecorderWidget caps recording strictly at 7.0 seconds', (tester) async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();
      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      double? capturedDuration;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileSetupControllerProvider.overrideWith((ref) => controller),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: VoiceSparkRecorderWidget(
                onRecordAudio: (duration) async {
                  capturedDuration = duration;
                  return [0x1F, 0x2F, 0x3F];
                },
              ),
            ),
          ),
        ),
      );

      expect(find.text('7-Second Voice Spark'), findsOneWidget);
      expect(find.text('0.0s / 7.0s'), findsOneWidget);

      // Tap microphone button to start recording
      await tester.tap(find.byIcon(Icons.mic_none_rounded));
      await tester.pump();

      expect(find.byIcon(Icons.stop_rounded), findsOneWidget);

      // Advance by 4 seconds
      await tester.pump(const Duration(seconds: 4));
      expect(find.textContaining('/ 7.0s'), findsOneWidget);

      // Advance by another 4 seconds (total 8s) -> auto-caps at 7.0s and stops recording
      await tester.pump(const Duration(seconds: 4));
      await tester.pumpAndSettle();

      expect(find.text('7.0s / 7.0s'), findsOneWidget);
      expect(find.byIcon(Icons.stop_rounded), findsNothing);
      expect(capturedDuration, 7.0);
      expect(find.text('Keep Voice Spark'), findsOneWidget);
    });

    testWidgets('Test 5: ProfileSetupScreen valid submission persists completed status and navigates to /main', (tester) async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/media/presigned-url') {
          return http.Response(
            jsonEncode({
              'upload_url': 'https://r2.cloudflare.com/slot-1',
              'public_cdn_url': 'https://media.urheart.app/slot_1.webp',
            }),
            200,
          );
        }
        if (url.path == '/api/v1/profile/create') {
          return http.Response(
            jsonEncode({
              'success': true,
              'data': {'id': 'user-123', 'is_profile_completed': true},
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      fakeHttp.onPut = (url, headers, body) async => http.Response('', 200);

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      final testRouter = GoRouter(
        initialLocation: '/profile-setup',
        routes: [
          GoRoute(
            path: '/profile-setup',
            builder: (context, state) => ProfileSetupScreen(
              onPickImage: (slot) async => [0xAA, 0xBB],
            ),
          ),
          GoRoute(
            path: '/main',
            builder: (context, state) => const Scaffold(body: Text('Main Discovery Deck')),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileSetupControllerProvider.overrideWith((ref) => controller),
          ],
          child: MaterialApp.router(
            routerConfig: testRouter,
          ),
        ),
      );

      expect(find.text('Craft Your Sacred Persona'), findsOneWidget);
      expect(find.text('Complete Profile & Enter Deck'), findsOneWidget);

      // 1. Tap Slot 1 at the top of the view to upload photo
      await tester.tap(find.text('Slot 1 — Primary Avatar'));
      await tester.pumpAndSettle();
      expect(controller.state.photoUrls[0], isNotNull);

      // 2. Enter Full Name
      await tester.enterText(find.widgetWithText(TextField, 'Full Name'), 'Mira Krishnan');
      await tester.pumpAndSettle();

      // 3. Enter Contact Bridge Handle
      final handleFinder = find.widgetWithText(TextField, 'Handle or Verified Number');
      await tester.ensureVisible(handleFinder);
      await tester.enterText(handleFinder, '+919988776655');
      await tester.pumpAndSettle();

      // 4. Tap CTA to complete profile
      final ctaFinder = find.text('Complete Profile & Enter Deck');
      await tester.ensureVisible(ctaFinder);
      await tester.tap(ctaFinder);
      await tester.pumpAndSettle();

      // Verification: Navigation to /main occurred
      expect(find.text('Main Discovery Deck'), findsOneWidget);

      // Verification: Session storage marked is_profile_completed
      final completed = await sessionStorage.readCustomKey('is_profile_completed');
      expect(completed, 'true');
    });

    test('Test 6: ProfileSetupState.copyWith distinguishes omitted from explicit null', () {
      const state = ProfileSetupState(
        avatarUrl: 'https://media.urheart.app/slot_1.webp',
        voiceSparkUrl: 'https://media.urheart.app/spark.m4a',
      );

      // Omitted: preserves existing values
      final omittedState = state.copyWith(fullName: 'Ananya');
      expect(omittedState.avatarUrl, 'https://media.urheart.app/slot_1.webp');
      expect(omittedState.voiceSparkUrl, 'https://media.urheart.app/spark.m4a');
      expect(omittedState.fullName, 'Ananya');

      // Explicit null: clears nullable values
      final clearedState = state.copyWith(avatarUrl: null, voiceSparkUrl: null);
      expect(clearedState.avatarUrl, isNull);
      expect(clearedState.voiceSparkUrl, isNull);
    });

    test('Test 7: Slot 1 upload updates avatarUrl even when previously set; removePhotoSlot clears avatar when empty', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onPost = (url, headers, body) async {
        final decoded = jsonDecode(body.toString());
        final slot = decoded['slot_number'] as int;
        return http.Response(
          jsonEncode({
            'success': true,
            'upload_url': 'https://r2.cloudflare.com/slot-$slot',
            'public_cdn_url': 'https://media.urheart.app/slot_$slot.webp',
          }),
          200,
        );
      };
      fakeHttp.onPut = (url, headers, body) async => http.Response('', 200);
      fakeHttp.onDelete = (url, headers, body) async => http.Response('{"success": true}', 200);

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      // 1. Upload Slot 2 first
      await controller.uploadPhotoSlot(2, [1, 2, 3]);
      expect(controller.state.avatarUrl, 'https://media.urheart.app/slot_2.webp');

      // 2. Upload Slot 1 -> must override avatarUrl to slot 1 CDN URL
      await controller.uploadPhotoSlot(1, [4, 5, 6]);
      expect(controller.state.avatarUrl, 'https://media.urheart.app/slot_1.webp');

      // 3. Remove Slot 1 -> avatar falls back to Slot 2
      await controller.removePhotoSlot(1);
      expect(controller.state.avatarUrl, 'https://media.urheart.app/slot_2.webp');

      // 4. Remove Slot 2 -> all photos removed, avatarUrl must be null
      await controller.removePhotoSlot(2);
      expect(controller.state.avatarUrl, isNull);
    });

    test('Test 8: submitProfile includes validated user_dob from session storage and does not fabricate false dob', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      Map<String, dynamic>? receivedPayload;
      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/media/presigned-url') {
          return http.Response(
            jsonEncode({
              'upload_url': 'https://r2.cloudflare.com/slot-1',
              'public_cdn_url': 'https://media.urheart.app/slot_1.webp',
            }),
            200,
          );
        }
        if (url.path == '/api/v1/profile/create') {
          receivedPayload = jsonDecode(body.toString()) as Map<String, dynamic>;
          return http.Response('{"success": true}', 200);
        }
        return http.Response('{}', 200);
      };
      fakeHttp.onPut = (url, headers, body) async => http.Response('', 200);

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      controller.updateTextFields(
        fullName: 'Devika Sen',
        contactBridgeHandle: '+919876543210',
      );
      await controller.uploadPhotoSlot(1, [1, 2, 3]);

      // Case A: No stored DOB -> 'dob' is omitted, NOT fabricated
      await controller.submitProfile();
      expect(receivedPayload?['dob'], isNull);

      // Case B: Valid stored DOB -> 'dob' is sent with exact stored value
      await sessionStorage.writeCustomKey('user_dob', '2001-08-24');
      await controller.submitProfile();
      expect(receivedPayload?['dob'], '2001-08-24');
    });

    testWidgets('Test 9: PhotoSlotGrid does not trigger upload when onPickImage is null', (tester) async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();
      var uploadCalled = false;
      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/media/presigned-url') {
          uploadCalled = true;
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileSetupControllerProvider.overrideWith((ref) => controller),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: PhotoSlotGrid(), // onPickImage is null
            ),
          ),
        ),
      );

      await tester.tap(find.text('Slot 1 — Primary Avatar'));
      await tester.pumpAndSettle();

      expect(uploadCalled, isFalse);
      expect(controller.state.photoUrls[0], isNull);
    });

    testWidgets('Test 10: VoiceSparkRecorderWidget disables recording and shows unavailable when onRecordAudio is null', (tester) async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();
      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileSetupControllerProvider.overrideWith((ref) => controller),
          ],
          child: const MaterialApp(
            home: Scaffold(
              body: VoiceSparkRecorderWidget(), // onRecordAudio is null
            ),
          ),
        ),
      );

      expect(find.text('Voice recording unavailable'), findsOneWidget);

      // Tapping the mic button does not start recording
      await tester.tap(find.byIcon(Icons.mic_none_rounded));
      await tester.pump();

      expect(find.byIcon(Icons.stop_rounded), findsNothing);
      expect(find.text('0.0s / 7.0s'), findsOneWidget);
      expect(find.text('Keep Voice Spark'), findsNothing);
    });

    testWidgets('Test 11: VoiceSparkRecorderWidget uploads pre-captured audio when Keep Voice Spark is tapped', (tester) async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/media/presigned-url') {
          return http.Response(
            jsonEncode({
              'upload_url': 'https://r2.cloudflare.com/voice-spark',
              'public_cdn_url': 'https://media.urheart.app/users/test/voice/spark.m4a',
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      List<int>? uploadedBytes;
      fakeHttp.onPut = (url, headers, body) async {
        if (body is List<int>) {
          uploadedBytes = body;
        }
        return http.Response('', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      final sampleAudio = [0x11, 0x22, 0x33, 0x44];
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileSetupControllerProvider.overrideWith((ref) => controller),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: VoiceSparkRecorderWidget(
                onRecordAudio: (duration) async => sampleAudio,
              ),
            ),
          ),
        ),
      );

      // Start recording
      await tester.tap(find.byIcon(Icons.mic_none_rounded));
      await tester.pump();

      // Stop recording at 2 seconds
      await tester.pump(const Duration(seconds: 2));
      await tester.tap(find.byIcon(Icons.stop_rounded));
      await tester.pumpAndSettle();

      expect(find.text('Keep Voice Spark'), findsOneWidget);

      // Tap Keep Voice Spark -> uploads pre-captured audio
      await tester.tap(find.text('Keep Voice Spark'));
      await tester.pumpAndSettle();

      expect(uploadedBytes, sampleAudio);
      expect(controller.state.voiceSparkUrl, 'https://media.urheart.app/users/test/voice/spark.m4a');
      expect(find.text('Voice Spark Preserved on Edge CDN'), findsOneWidget);
    });

    test('Test 12: ProfileSetupController.initializeForEdit hydrates existing profile data and sets isEditMode to true', () {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();
      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);

      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      final existingData = {
        'full_name': 'Meera Krishnan',
        'bio': 'Conscious architect and tea enthusiast.',
        'profession': 'Architect',
        'education': 'CEPT University',
        'gender': 'Woman',
        'interested_in': 'Men',
        'contact_bridge_type': 'whatsapp',
        'contact_bridge_handle': '+919876543210',
        'avatar_url': 'https://media.urheart.app/slot_1.webp',
        'photos': ['https://media.urheart.app/slot_1.webp', 'https://media.urheart.app/slot_2.webp'],
      };

      controller.initializeForEdit(profileData: existingData);

      expect(controller.state.isEditMode, isTrue);
      expect(controller.state.fullName, 'Meera Krishnan');
      expect(controller.state.bio, 'Conscious architect and tea enthusiast.');
      expect(controller.state.profession, 'Architect');
      expect(controller.state.avatarUrl, 'https://media.urheart.app/slot_1.webp');
      expect(controller.state.photoUrls[0], 'https://media.urheart.app/slot_1.webp');
      expect(controller.state.photoUrls[1], 'https://media.urheart.app/slot_2.webp');
      expect(controller.state.photoUrls[2], isNull);
    });

    test('Test 13: submitProfile dispatches PUT /api/v1/profile with ProfileUpdate schema when isEditMode is true', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      Uri? capturedPutUri;
      Map<String, dynamic>? capturedPutBody;
      bool postCalled = false;

      fakeHttp.onPut = (url, headers, body) async {
        capturedPutUri = url;
        if (body != null) {
          capturedPutBody = jsonDecode(body.toString()) as Map<String, dynamic>;
        }
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {'id': 'test-uuid', 'full_name': 'Meera K.'},
            'message': 'Profile updated successfully.',
          }),
          200,
        );
      };

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/profile/create') {
          postCalled = true;
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      controller.initializeForEdit(profileData: {
        'full_name': 'Meera Krishnan',
        'bio': 'Initial bio',
        'profession': 'Architect',
        'education': 'CEPT',
        'photos': ['https://media.urheart.app/slot_1.webp'],
        'avatar_url': 'https://media.urheart.app/slot_1.webp',
      });

      // User edits bio and name
      controller.updateTextFields(
        fullName: 'Meera K.',
        bio: 'Updated conscious bio for sacred reflections.',
      );

      final success = await controller.submitProfile();

      expect(success, isTrue);
      expect(postCalled, isFalse, reason: 'Must not call POST /api/v1/profile/create when editing');
      expect(capturedPutUri?.path, '/api/v1/profile');
      expect(capturedPutBody?['full_name'], 'Meera K.');
      expect(capturedPutBody?['bio'], 'Updated conscious bio for sacred reflections.');
      expect(capturedPutBody?['profession'], 'Architect');
      expect(capturedPutBody?['photos'], ['https://media.urheart.app/slot_1.webp']);
      expect(capturedPutBody?['avatar_url'], 'https://media.urheart.app/slot_1.webp');

      // Strict extra fields verification: immutable/extra fields must NOT be in PUT body
      expect(capturedPutBody?.containsKey('dob'), isFalse);
      expect(capturedPutBody?.containsKey('contact_bridge_raw'), isFalse);
      expect(capturedPutBody?.containsKey('gender'), isFalse);
    });

    test('Test 14: checkProfileCompletion detects completed profile from storage and switches to edit mode for PUT', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      await sessionStorage.writeCustomKey('is_profile_completed', 'true');

      final fakeHttp = FakeHttpClient();
      Uri? capturedPutUri;
      fakeHttp.onPut = (url, headers, body) async {
        capturedPutUri = url;
        return http.Response('{"success": true}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      final isCompleted = await controller.checkProfileCompletion();
      expect(isCompleted, isTrue);
      expect(controller.state.isEditMode, isTrue);

      controller.updateTextFields(
        fullName: 'Devika Sen',
        bio: 'Deep connection seeker',
        contactBridgeHandle: '+919988776655',
      );
      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/media/presigned-url') {
          return http.Response(
            jsonEncode({
              'upload_url': 'https://r2.cloudflare.com/slot-1',
              'public_cdn_url': 'https://media.urheart.app/slot_1.webp',
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };
      await controller.uploadPhotoSlot(1, [1, 2, 3]);

      final success = await controller.submitProfile();

      expect(success, isTrue);
      expect(capturedPutUri?.path, '/api/v1/profile');
    });

    test('Test 15: submitProfile handles backend HTTP 400/422 failure gracefully and populates errorMessage without crashing', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onPut = (url, headers, body) async {
        return http.Response(
          jsonEncode({
            'error_code': 'VALIDATION_ERROR',
            'message': 'Bio length exceeded maximum character limit.',
          }),
          400,
          headers: {'Content-Type': 'application/json'},
        );
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      controller.initializeForEdit(profileData: {
        'full_name': 'Ananya Das',
        'photos': ['https://media.urheart.app/slot_1.webp'],
      });

      final success = await controller.submitProfile();

      expect(success, isFalse);
      expect(controller.state.isSubmitting, isFalse);
      expect(controller.state.errorMessage, contains('Bio length exceeded'));
    });
  });
}
