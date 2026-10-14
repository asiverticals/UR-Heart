import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/profile_setup/presentation/controllers/profile_setup_controller.dart';
import 'package:ur_heart/features/profile_setup/presentation/widgets/kyc_liveness_modal.dart';

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
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onPost;
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onPut;

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
    return http.Response('', 200);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Phase 4 — Chunk 4.3: Groq Facial Liveness & Biometric Purge Tests', () {
    testWidgets('Test 1: KycLivenessModal displays statutory DPDP notice and renders circular camera viewfinder', (tester) async {
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
              body: KycLivenessModal(),
            ),
          ),
        ),
      );

      expect(find.text('Sacred Liveness Verification'), findsOneWidget);
      expect(find.textContaining('permanently incinerated in <60s under DPDP Act'), findsOneWidget);
      expect(find.byIcon(Icons.face_retouching_natural_rounded), findsOneWidget);
      expect(find.text('Begin 3s Check'), findsOneWidget);
    });

    testWidgets('Test 2: State transitions accurately from ready -> countdown -> analyzing -> approved', (tester) async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/kyc/presigned-upload') {
          return http.Response(
            jsonEncode({
              'upload_url': 'https://r2.cloudflare.com/kyc-temp',
              'object_key': 'kyc_temp/user_123/liveness_test.webp',
              'expires_in': 120,
            }),
            200,
          );
        }
        if (url.path == '/api/v1/kyc/verify-liveness') {
          return http.Response(
            jsonEncode({
              'success': true,
              'status': 'approved',
              'score': 88,
              'message': 'Identity Confirmed',
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

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            profileSetupControllerProvider.overrideWith((ref) => controller),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: KycLivenessModal(
                onCaptureLiveFrame: () async => [0xAA, 0xBB, 0xCC],
              ),
            ),
          ),
        ),
      );

      // 1. Tap Begin 3s Check
      await tester.tap(find.text('Begin 3s Check'));
      await tester.pump();

      // In countdown state
      expect(find.text('3'), findsOneWidget);
      expect(find.text('Blink naturally into frame...'), findsOneWidget);

      // Advance 1s -> 2
      await tester.pump(const Duration(seconds: 1));
      expect(find.text('2'), findsOneWidget);

      // Advance 1s -> 1
      await tester.pump(const Duration(seconds: 1));
      expect(find.text('1'), findsOneWidget);

      // Advance 1s -> countdown finishes, enters analyzing
      await tester.pump(const Duration(seconds: 1));
      // Pump async submitKycLiveness response
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.text('Identity Confirmed'), findsOneWidget);
      expect(find.text('Biometrics incinerated under DPDP Sec 8.'), findsOneWidget);
      expect(controller.state.isKycVerified, isTrue);

      // Advance through delayed auto-pop
      await tester.pump(const Duration(milliseconds: 1600));
      await tester.pump();
    });

    test('Test 3: ProfileSetupController.submitKycLiveness coordinates ephemeral upload and verification', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      Uri? presignedRequestedUrl;
      Uri? putUrl;
      List<int>? putBody;
      String? verifyBody;

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/kyc/presigned-upload') {
          presignedRequestedUrl = url;
          return http.Response(
            jsonEncode({
              'upload_url': 'https://r2.cloudflare.com/put/kyc_temp/user/frame.webp',
              'object_key': 'kyc_temp/user/frame.webp',
            }),
            200,
          );
        }
        if (url.path == '/api/v1/kyc/verify-liveness') {
          verifyBody = body?.toString();
          return http.Response(
            jsonEncode({
              'success': true,
              'status': 'approved',
              'score': 95,
              'message': 'Sacred identity verified.',
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      fakeHttp.onPut = (url, headers, body) async {
        putUrl = url;
        if (body is List<int>) putBody = body;
        return http.Response('', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: fakeHttp,
        storage: sessionStorage,
      );

      final sampleFrame = [0x52, 0x49, 0x46, 0x46, 0x01, 0x02];
      final verified = await controller.submitKycLiveness(sampleFrame);

      expect(verified, isTrue);
      expect(presignedRequestedUrl?.path, '/api/v1/kyc/presigned-upload');
      expect(putUrl?.toString(), 'https://r2.cloudflare.com/put/kyc_temp/user/frame.webp');
      expect(putBody, sampleFrame);
      expect(verifyBody, contains('kyc_temp/user/frame.webp'));
      expect(controller.state.isKycVerified, isTrue);
      expect(controller.state.kycStatus, 'approved');
      expect(controller.state.kycStatusMessage, 'Sacred identity verified.');
    });

    testWidgets('Test 4: KycLivenessModal transitions to rejected when onCaptureLiveFrame is null (no synthetic fallback)', (tester) async {
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
              body: KycLivenessModal(
                onCaptureLiveFrame: null, // Null capture callback
              ),
            ),
          ),
        ),
      );

      // Tap Begin 3s Check
      await tester.tap(find.text('Begin 3s Check'));
      await tester.pump();

      // Countdown 3 -> 2 -> 1 -> trigger capture
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));
      await tester.pump();

      // Should be rejected with error, not uploading synthetic 0xAA bytes
      expect(find.text('Unable to capture live selfie frame.'), findsOneWidget);
      expect(find.text('Retry Check'), findsOneWidget);
    });

    testWidgets('Test 5: KycLivenessModal transitions to escalated based on backend status without depending on message copy', (tester) async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/kyc/presigned-upload') {
          return http.Response(
            jsonEncode({
              'upload_url': 'https://r2.cloudflare.com/kyc-temp',
              'object_key': 'kyc_temp/user_123/liveness_test.webp',
            }),
            200,
          );
        }
        if (url.path == '/api/v1/kyc/verify-liveness') {
          return http.Response(
            jsonEncode({
              'success': true,
              'status': 'escalated',
              'score': 65,
              'message': 'Borderline liveness score. Senior sanctuary officer assigned.', // Message doesn't contain 'review'
            }),
            200,
          );
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
          child: MaterialApp(
            home: Scaffold(
              body: KycLivenessModal(
                onCaptureLiveFrame: () async => [0x11, 0x22],
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Begin 3s Check'));
      await tester.pump();

      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(find.text('Dossier Under Sanctuary Review'), findsOneWidget);
      expect(find.text('Borderline liveness score. Senior sanctuary officer assigned.'), findsOneWidget);
      expect(find.byIcon(Icons.hourglass_top_rounded), findsOneWidget);
    });

    test('Test 6: ProfileSetupState.copyWith distinguishes omitted from explicit null for kycStatus and kycStatusMessage', () {
      const stateWithKyc = ProfileSetupState(
        isKycVerified: true,
        kycStatus: 'approved',
        kycStatusMessage: 'Verified successfully',
      );

      // 1. Omitted args should preserve existing values
      final preserved = stateWithKyc.copyWith(fullName: 'Seeker');
      expect(preserved.kycStatus, 'approved');
      expect(preserved.kycStatusMessage, 'Verified successfully');

      // 2. Explicit null should clear them via _unset sentinel
      final cleared = stateWithKyc.copyWith(
        kycStatus: null,
        kycStatusMessage: null,
      );
      expect(cleared.kycStatus, isNull);
      expect(cleared.kycStatusMessage, isNull);
    });
  });
}
