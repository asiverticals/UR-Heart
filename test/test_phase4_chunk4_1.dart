import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/services/device_fingerprint_service.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/auth/presentation/controllers/auth_controller.dart';
import 'package:ur_heart/features/auth/presentation/screens/age_gate_auth_screen.dart';
import 'package:ur_heart/features/auth/presentation/screens/consent_screen.dart';
import 'package:ur_heart/features/auth/presentation/widgets/underage_quarantine_dialog.dart';

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

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Phase 4 — Chunk 4.1: Auth & Quarantine Tests', () {
    test('DeviceFingerprintService generates and persists 64-char hex anchor', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final service = DeviceFingerprintService(sessionStorage);

      final fp1 = await service.getOrCreateFingerprint();
      expect(fp1.length, 64);
      expect(RegExp(r'^[0-9a-f]{64}$').hasMatch(fp1), isTrue);

      final fp2 = await service.getOrCreateFingerprint();
      expect(fp2, fp1);
    });

    test('DeviceFingerprintService handles concurrent calls atomically', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final service = DeviceFingerprintService(sessionStorage);

      final results = await Future.wait([
        service.getOrCreateFingerprint(),
        service.getOrCreateFingerprint(),
        service.getOrCreateFingerprint(),
      ]);

      expect(results[0], results[1]);
      expect(results[1], results[2]);
      expect(results[0].length, 64);
    });

    test('AuthController accurately calculates age and updates eligibility with referenceDate', () {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final client = SanctuaryHttpClient(sessionStorage, client: FakeHttpClient());
      final fpService = DeviceFingerprintService(sessionStorage);

      final controller = AuthController(
        client: client,
        storage: sessionStorage,
        fingerprintService: fpService,
      );

      final referenceDate = DateTime(2026, 6, 15);
      // Exactly 20 years ago today
      final adultDob = DateTime(2006, 6, 15);
      controller.updateDob(adultDob, referenceDate: referenceDate);

      expect(controller.state.selectedDob, adultDob);
      expect(controller.state.calculatedAge, 20);
      expect(controller.state.isEligible, isTrue);
      expect(controller.state.isServerApproved, isFalse);

      // Tomorrow would be 18th birthday -> still 17 today!
      final underageDob = DateTime(2008, 6, 16);
      controller.updateDob(underageDob, referenceDate: referenceDate);

      expect(controller.state.calculatedAge, 17);
      expect(controller.state.isEligible, isFalse);
      expect(controller.state.isServerApproved, isFalse);
    });

    test('AuthController.verifyAgeAndRegisterIntent satisfies eligibility on 200 OK', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final mockClient = FakeHttpClient();

      mockClient.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/auth/register-intent') {
          return http.Response('{"data": {"eligible": true}, "message": "Age criteria satisfied."}', 200);
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: mockClient);
      final fpService = DeviceFingerprintService(sessionStorage);

      final controller = AuthController(
        client: client,
        storage: sessionStorage,
        fingerprintService: fpService,
      );

      controller.updateDob(DateTime(2000, 1, 1));
      expect(controller.state.isServerApproved, isFalse);

      final result = await controller.verifyAgeAndRegisterIntent();

      expect(result, isTrue);
      expect(controller.state.isEligible, isTrue);
      expect(controller.state.isServerApproved, isTrue);
      expect(controller.state.isUnderageQuarantined, isFalse);
    });

    test('AuthController.verifyAgeAndRegisterIntent discards response if DOB was updated in-flight', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final mockClient = FakeHttpClient();

      mockClient.onPost = (url, headers, body) async {
        await Future.delayed(const Duration(milliseconds: 20));
        return http.Response('{"data": {"eligible": true}}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: mockClient);
      final fpService = DeviceFingerprintService(sessionStorage);

      final controller = AuthController(
        client: client,
        storage: sessionStorage,
        fingerprintService: fpService,
      );

      controller.updateDob(DateTime(2000, 1, 1));
      final future = controller.verifyAgeAndRegisterIntent();

      final newDob = DateTime(2005, 5, 5);
      controller.updateDob(newDob);

      final result = await future;

      expect(result, isFalse);
      expect(controller.state.selectedDob, newDob);
      expect(controller.state.isServerApproved, isFalse);
    });

    test('AuthController.verifyAgeAndRegisterIntent locks into quarantine on 403 with UNDERAGE_QUARANTINE_TRIGGERED', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final mockClient = FakeHttpClient();

      mockClient.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/auth/register-intent') {
          return http.Response(
            jsonEncode({
              'error_code': 'UNDERAGE_QUARANTINE_TRIGGERED',
              'message': 'Seeker is under the legal age threshold.',
            }),
            403,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: mockClient);
      final fpService = DeviceFingerprintService(sessionStorage);

      final controller = AuthController(
        client: client,
        storage: sessionStorage,
        fingerprintService: fpService,
      );

      controller.updateDob(DateTime(2010, 1, 1), referenceDate: DateTime(2026, 6, 15));
      final result = await controller.verifyAgeAndRegisterIntent();

      expect(result, isFalse);
      expect(controller.state.isEligible, isFalse);
      expect(controller.state.isUnderageQuarantined, isTrue);
      expect(controller.state.quarantineUntil, isNotNull);
    });

    test('AuthController.verifyAgeAndRegisterIntent does not quarantine on non-quarantine 403', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final mockClient = FakeHttpClient();

      mockClient.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/auth/register-intent') {
          return http.Response(
            jsonEncode({
              'error_code': 'FORBIDDEN_ZONE',
              'message': 'Access to this endpoint is restricted.',
            }),
            403,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: mockClient);
      final fpService = DeviceFingerprintService(sessionStorage);

      final controller = AuthController(
        client: client,
        storage: sessionStorage,
        fingerprintService: fpService,
      );

      controller.updateDob(DateTime(2000, 1, 1));
      final result = await controller.verifyAgeAndRegisterIntent();

      expect(result, isFalse);
      expect(controller.state.isServerApproved, isFalse);
      expect(controller.state.isUnderageQuarantined, isFalse);
      expect(controller.state.quarantineUntil, isNull);
      expect(controller.state.errorMessage, 'Access to this endpoint is restricted.');
    });

    test('AuthController.sendMagicLink dispatches single-use email link', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final mockClient = FakeHttpClient();

      String? sentPayload;
      mockClient.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/auth/send-magic-link') {
          sentPayload = body?.toString();
          return http.Response('{"data": {"dispatched": true}}', 200);
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: mockClient);
      final fpService = DeviceFingerprintService(sessionStorage);

      final controller = AuthController(
        client: client,
        storage: sessionStorage,
        fingerprintService: fpService,
      );

      final ok = await controller.sendMagicLink('seeker@sanctuary.in');
      expect(ok, isTrue);
      expect(controller.state.magicLinkSentEmail, 'seeker@sanctuary.in');
      expect(sentPayload, contains('seeker@sanctuary.in'));
    });

    test('AuthController.syncGoogleUser exchanges idToken, validates payload, and saves role', () async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final mockClient = FakeHttpClient();

      // 1. Missing user_id should fail
      mockClient.onPost = (url, headers, body) async {
        return http.Response(
          jsonEncode({
            'access_token': 'jwt-access',
            'refresh_token': 'jwt-refresh',
            'user_id': '',
            'role': 'curator',
          }),
          200,
        );
      };

      final client = SanctuaryHttpClient(sessionStorage, client: mockClient);
      final fpService = DeviceFingerprintService(sessionStorage);

      final controller = AuthController(
        client: client,
        storage: sessionStorage,
        fingerprintService: fpService,
      );

      final failResult = await controller.syncGoogleUser('google-token');
      expect(failResult, isFalse);
      expect(controller.state.errorMessage, contains('missing tokens or user ID'));
      expect(await sessionStorage.readAuthToken(), isNull);

      // 2. Valid payload with dynamic role
      mockClient.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/auth/google-sync') {
          return http.Response(
            jsonEncode({
              'access_token': 'jwt-google-access',
              'refresh_token': 'jwt-google-refresh',
              'user_id': '00000000-0000-0000-0000-000000000001',
              'role': 'curator',
              'is_profile_completed': true,
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      final success = await controller.syncGoogleUser('google-test-id-token');
      expect(success, isTrue);
      expect(await sessionStorage.readAuthToken(), 'jwt-google-access');
      expect(await sessionStorage.readRefreshToken(), 'jwt-google-refresh');
      expect(await sessionStorage.readUserId(), '00000000-0000-0000-0000-000000000001');
      expect(await sessionStorage.readUserRole(), 'curator');
    });

    testWidgets('UnderageQuarantineDialog renders non-dismissible lockout modal', (tester) async {
      final quarantineDate = DateTime.now().add(const Duration(days: 180));

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: UnderageQuarantineDialog(
              quarantineUntil: quarantineDate,
            ),
          ),
        ),
      );

      expect(find.text('Sacred Boundary Enforced'), findsOneWidget);
      expect(find.byIcon(Icons.gavel_rounded), findsOneWidget);
      expect(find.textContaining('POCSO'), findsOneWidget);
      expect(find.textContaining('Hardware Lockout:'), findsOneWidget);
      expect(find.textContaining('Days Remaining'), findsOneWidget);
      expect(find.textContaining('statutory child safety mandates'), findsOneWidget);

      final popScope = tester.widget<PopScope>(find.byType(PopScope));
      expect(popScope.canPop, isFalse);
    });

    testWidgets('ConsentScreen renders 3 cards, persists DPDP consent record, and navigates', (tester) async {
      final testRouter = GoRouter(
        initialLocation: '/consent',
        routes: [
          GoRoute(
            path: '/consent',
            builder: (context, state) => const ConsentScreen(),
          ),
          GoRoute(
            path: '/auth',
            builder: (context, state) => const Scaffold(body: Text('Auth Gate Screen')),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: testRouter,
          ),
        ),
      );

      expect(find.text('Welcome to UR-Heart Sanctuary'), findsOneWidget);
      expect(find.text('DPDP Section 6 Purpose Limitation'), findsOneWidget);
      expect(find.text('FLAG_SECURE Anti-Capture Shield'), findsOneWidget);
      expect(find.text('10-Swipe Daily Mindful Rhythm'), findsOneWidget);
      expect(find.text('I Affirm & Enter the Sanctuary'), findsOneWidget);

      // Initially all checkboxes are false -> Affirm All Clause action
      expect(find.text('Affirm All Clauses'), findsOneWidget);

      // Tap "Affirm All Clauses"
      await tester.tap(find.text('Affirm All Clauses'));
      await tester.pumpAndSettle();

      expect(find.text('Deselect All'), findsOneWidget);

      // Tap "I Affirm & Enter the Sanctuary" CTA
      await tester.tap(find.text('I Affirm & Enter the Sanctuary'));
      await tester.pumpAndSettle();

      // Verify navigation to /auth occurred
      expect(find.text('Auth Gate Screen'), findsOneWidget);

      // Verify SharedPreferences has persisted the statutory consent record
      final prefs = await SharedPreferences.getInstance();
      final consentJson = prefs.getString(ConsentScreen.consentRecordKey);
      expect(consentJson, isNotNull);
      final decoded = jsonDecode(consentJson!) as Map<String, dynamic>;
      expect(decoded['version'], '1.0');
      expect(decoded['purpose_limitation'], isTrue);
      expect(decoded['flag_secure_anti_capture'], isTrue);
      expect(decoded['rhythm_10_swipe'], isTrue);
      expect(decoded['timestamp'], isNotNull);
    });

    testWidgets('AgeGateAuthScreen shows date selector, age badge, and unlocks auth on 18+', (tester) async {
      final fakeStorage = TestSecureStorage();
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final mockClient = FakeHttpClient();

      mockClient.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/auth/register-intent') {
          return http.Response('{"data": {"eligible": true}}', 200);
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: mockClient);
      final fpService = DeviceFingerprintService(sessionStorage);

      final controller = AuthController(
        client: client,
        storage: sessionStorage,
        fingerprintService: fpService,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authControllerProvider.overrideWith((ref) => controller),
          ],
          child: const MaterialApp(
            home: AgeGateAuthScreen(),
          ),
        ),
      );

      expect(find.text('Declare Your Age'), findsOneWidget);
      expect(find.text('Date of Birth'), findsOneWidget);
      expect(find.text('Continue with Google'), findsNothing);

      // Manually set adult DOB in controller
      controller.updateDob(DateTime(2000, 5, 20), referenceDate: DateTime(2026, 6, 15));
      await tester.pumpAndSettle();

      // Before server approval, verified badge and Google button must NOT be unlocked!
      expect(find.textContaining('Verified 18+'), findsNothing);
      expect(find.text('Continue with Google'), findsNothing);

      // Now invoke server verification
      await controller.verifyAgeAndRegisterIntent();
      await tester.pumpAndSettle();

      // Verified 18+ badge and Google / Magic Link fields should now be unlocked!
      expect(find.textContaining('Verified 18+'), findsOneWidget);
      expect(find.text('Continue with Google'), findsOneWidget);
      expect(find.text('Send Sacred Link'), findsOneWidget);
    });
  });
}
