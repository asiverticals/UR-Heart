import 'dart:async';
import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/profile_setup/presentation/controllers/profile_setup_controller.dart';
import 'package:ur_heart/features/resonances/presentation/controllers/resonances_controller.dart';

class MockSecureStorage extends Fake implements FlutterSecureStorage {
  final Map<String, String> _storage = {};

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
      _storage[key] = value;
    } else {
      _storage.remove(key);
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
    return _storage[key];
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
    _storage.remove(key);
  }
}

class AdversarialHttpClient extends Fake implements http.Client {
  Future<http.Response> Function(Uri url, Map<String, String>? headers)? onGet;
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onPost;
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onPut;
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onDelete;

  @override
  Future<http.Response> get(Uri url, {Map<String, String>? headers}) async {
    if (onGet != null) return onGet!(url, headers);
    return http.Response('{"data": []}', 200);
  }

  @override
  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    if (onPost != null) return onPost!(url, headers, body);
    return http.Response('{"data": {}}', 200);
  }

  @override
  Future<http.Response> put(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    if (onPut != null) return onPut!(url, headers, body);
    return http.Response('{"data": {}}', 200);
  }

  @override
  Future<http.Response> delete(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    if (onDelete != null) return onDelete!(url, headers, body);
    return http.Response('{"data": {}}', 200);
  }

  @override
  void close() {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Adversarial Challenge: ResonancesController Payload Formatting & Error Handling', () {
    late MockSecureStorage mockStorage;
    late SecureSessionStorage sessionStorage;
    late AdversarialHttpClient mockHttp;
    late SanctuaryHttpClient client;

    setUp(() {
      mockStorage = MockSecureStorage();
      sessionStorage = SecureSessionStorage(storage: mockStorage);
      mockHttp = AdversarialHttpClient();
      client = SanctuaryHttpClient(sessionStorage, client: mockHttp);
    });

    test('Empirically verify payload formatting for swipeType "like", "pass", and "superlike" — NO "swipe_type" sent', () async {
      final actionsTested = ['like', 'pass', 'superlike'];

      for (final action in actionsTested) {
        Map<String, dynamic>? capturedBody;
        Uri? capturedUri;

        mockHttp.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/feed/swipe') {
            capturedUri = url;
            capturedBody = jsonDecode(body.toString()) as Map<String, dynamic>;
            return http.Response(
              jsonEncode({
                'is_match': false,
                'match_id': null,
                'swipes_remaining': 8,
              }),
              200,
            );
          }
          return http.Response('{"data": []}', 200);
        };

        mockHttp.onGet = (url, headers) async {
          return http.Response('{"data": []}', 200);
        };

        final controller = ResonancesController(client);
        final targetId = 'target-uuid-$action';

        // Call via swipeType parameter
        final res = await controller.respondToSwipe(
          targetId: targetId,
          swipeType: action,
        );

        expect(res, isTrue, reason: 'Swipe for $action should return true on success');
        expect(capturedUri?.path, '/api/v1/feed/swipe');
        expect(capturedBody, isNotNull);
        expect(capturedBody!['target_id'], targetId);
        expect(capturedBody!['action'], action);

        // CRITICAL ADVERSARIAL ASSERTION: No 'swipe_type' payload key allowed
        expect(
          capturedBody!.containsKey('swipe_type'),
          isFalse,
          reason: 'CRITICAL: Payload MUST NOT contain key "swipe_type" which breaks FastAPI ConfigDict(extra="forbid")',
        );

        // Verify no extra forbidden keys
        final allowedKeys = {'target_id', 'action'};
        for (final key in capturedBody!.keys) {
          expect(allowedKeys.contains(key), isTrue, reason: 'Payload contains unexpected key: $key');
        }
      }
    });

    test('Empirically verify payload formatting when using action parameter instead of swipeType', () async {
      final actions = ['like', 'pass', 'superlike'];

      for (final act in actions) {
        Map<String, dynamic>? capturedBody;
        mockHttp.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/feed/swipe') {
            capturedBody = jsonDecode(body.toString()) as Map<String, dynamic>;
            return http.Response(
              jsonEncode({'is_match': false, 'swipes_remaining': 5}),
              200,
            );
          }
          return http.Response('{"data": []}', 200);
        };
        mockHttp.onGet = (url, headers) async => http.Response('{"data": []}', 200);

        final controller = ResonancesController(client);
        final res = await controller.respondToSwipe(
          targetId: 'target-uuid-param-$act',
          action: act,
        );

        expect(res, isTrue);
        expect(capturedBody!['action'], act);
        expect(capturedBody!.containsKey('swipe_type'), isFalse);
      }
    });

    test('Empirically verify fallback to "like" when neither swipeType nor action is specified', () async {
      Map<String, dynamic>? capturedBody;
      mockHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/feed/swipe') {
          capturedBody = jsonDecode(body.toString()) as Map<String, dynamic>;
          return http.Response(jsonEncode({'is_match': false}), 200);
        }
        return http.Response('{}', 200);
      };
      mockHttp.onGet = (url, headers) async => http.Response('{"data": []}', 200);

      final controller = ResonancesController(client);
      final res = await controller.respondToSwipe(targetId: 'target-fallback');

      expect(res, isTrue);
      expect(capturedBody!['action'], 'like');
      expect(capturedBody!.containsKey('swipe_type'), isFalse);
    });

    test('Adversarial: Concurrent double-tap on same targetId is dropped by pending lock', () async {
      final completer = Completer<http.Response>();
      int postCount = 0;

      mockHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/feed/swipe') {
          postCount++;
          return completer.future;
        }
        return http.Response('{}', 200);
      };
      mockHttp.onGet = (url, headers) async => http.Response('{"data": []}', 200);

      final controller = ResonancesController(client);

      // Trigger first swipe (uncompleted)
      final future1 = controller.respondToSwipe(targetId: 'same-target', swipeType: 'like');

      // Trigger immediate second swipe on same target
      final future2 = controller.respondToSwipe(targetId: 'same-target', swipeType: 'like');

      // Immediate second swipe should return false without duplicate post
      final res2 = await future2;
      expect(res2, isFalse, reason: 'Duplicate swipe on pending target must return false immediately');

      // Now complete the first HTTP call
      completer.complete(http.Response(jsonEncode({'is_match': false}), 200));
      final res1 = await future1;
      expect(res1, isTrue);
      expect(postCount, 1, reason: 'Backend must only receive exactly 1 swipe request for the target');
    });

    test('Adversarial: Simulated HTTP 422, 403, and 500 errors safely populate state.error without unhandled exceptions', () async {
      final errorCases = [
        {'status': 422, 'code': 'UNPROCESSABLE_ENTITY', 'msg': 'Validation error on action field'},
        {'status': 403, 'code': 'DAILY_QUOTA_EXHAUSTED', 'msg': 'Daily quota exhausted'},
        {'status': 500, 'code': 'INTERNAL_ERROR', 'msg': 'Database cluster connection failed'},
      ];

      for (final testCase in errorCases) {
        mockHttp.onPost = (url, headers, body) async {
          if (url.path == '/api/v1/feed/swipe') {
            return http.Response(
              jsonEncode({
                'error_code': testCase['code'],
                'message': testCase['msg'],
              }),
              testCase['status'] as int,
              headers: {'Content-Type': 'application/json'},
            );
          }
          return http.Response('{}', 200);
        };
        mockHttp.onGet = (url, headers) async => http.Response('{"data": []}', 200);

        final controller = ResonancesController(client);

        // Ensure calling does NOT throw an unhandled exception
        bool? result;
        expect(() async {
          result = await controller.respondToSwipe(
            targetId: 'target-err-${testCase['status']}',
            swipeType: 'like',
          );
        }, returnsNormally);

        await Future<void>.delayed(const Duration(milliseconds: 10));

        expect(result, isFalse);
        expect(
          controller.state.error,
          testCase['msg'],
          reason: 'state.error must contain verbatim backend error message',
        );

        // Verify clearError resets it
        controller.clearError();
        expect(controller.state.error, isNull);
      }
    });

    test('Adversarial: Simulated low-level network failure (SocketException/ClientException) populates state.error without crashing', () async {
      mockHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/feed/swipe') {
          throw http.ClientException('Connection reset by peer');
        }
        return http.Response('{}', 200);
      };
      mockHttp.onGet = (url, headers) async => http.Response('{"data": []}', 200);

      final controller = ResonancesController(client);

      final result = await controller.respondToSwipe(
        targetId: 'target-network-crash',
        swipeType: 'like',
      );

      expect(result, isFalse);
      expect(controller.state.error, isNotNull);
      expect(controller.state.error, contains('Connection reset by peer'));
    });
  });

  group('Adversarial Challenge: ProfileSetupController State Handling & Immutable Field Isolation', () {
    late MockSecureStorage mockStorage;
    late SecureSessionStorage sessionStorage;
    late AdversarialHttpClient mockHttp;
    late SanctuaryHttpClient client;

    setUp(() {
      mockStorage = MockSecureStorage();
      sessionStorage = SecureSessionStorage(storage: mockStorage);
      mockHttp = AdversarialHttpClient();
      client = SanctuaryHttpClient(sessionStorage, client: mockHttp);
    });

    test('CRITICAL: In edit mode (isEditMode == true), PUT /api/v1/profile is called and onboarding immutable fields (dob, gender, contact_bridge_raw) are strictly OMITTED', () async {
      Uri? capturedUri;
      Map<String, dynamic>? capturedBody;
      bool postCreateCalled = false;

      mockHttp.onPut = (url, headers, body) async {
        if (url.path == '/api/v1/profile') {
          capturedUri = url;
          if (body != null) {
            capturedBody = jsonDecode(body.toString()) as Map<String, dynamic>;
          }
        }
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {'id': 'test-uuid', 'full_name': 'Aanya Sengupta'},
            'message': 'Profile updated successfully.',
          }),
          200,
          headers: {'Content-Type': 'application/json'},
        );
      };

      mockHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/profile/create') {
          postCreateCalled = true;
        }
        return http.Response('{}', 200);
      };

      // Populate local storage with sensitive onboarding data
      await sessionStorage.writeCustomKey('user_dob', '1998-05-14');
      await sessionStorage.writeCustomKey('is_profile_completed', 'true');

      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: mockHttp,
        storage: sessionStorage,
      );

      // Hydrate state via initializeForEdit with rich persona data
      controller.initializeForEdit(profileData: {
        'full_name': 'Aanya Sengupta',
        'bio': 'Passionate about heritage conservation and sitar music.',
        'profession': 'Heritage Architect',
        'education': 'Jadavpur University',
        'gender': 'Woman',
        'interested_in': 'Men',
        'contact_bridge_type': 'whatsapp',
        'contact_bridge_handle': '+919830012345',
        'contact_bridge_raw': '+919830012345',
        'dob': '1998-05-14',
        'avatar_url': 'https://media.urheart.app/slot_1.webp',
        'photos': ['https://media.urheart.app/slot_1.webp', 'https://media.urheart.app/slot_2.webp'],
      });

      expect(controller.state.isEditMode, isTrue);

      // Update mutable text fields
      controller.updateTextFields(
        fullName: 'Aanya S.',
        bio: 'Updated bio: Architect & classical vocalist.',
        profession: 'Principal Architect',
        education: 'JU & CEPT',
      );

      final success = await controller.submitProfile();

      expect(success, isTrue);
      expect(postCreateCalled, isFalse, reason: 'CRITICAL: POST /api/v1/profile/create must NEVER be invoked in edit mode!');
      expect(capturedUri?.path, '/api/v1/profile', reason: 'PUT /api/v1/profile must be called in edit mode');
      expect(capturedBody, isNotNull);

      // Verify mutable fields ARE included
      expect(capturedBody!['full_name'], 'Aanya S.');
      expect(capturedBody!['bio'], 'Updated bio: Architect & classical vocalist.');
      expect(capturedBody!['profession'], 'Principal Architect');
      expect(capturedBody!['education'], 'JU & CEPT');
      expect(capturedBody!['interested_in'], 'Men');
      expect(capturedBody!['photos'], ['https://media.urheart.app/slot_1.webp', 'https://media.urheart.app/slot_2.webp']);
      expect(capturedBody!['avatar_url'], 'https://media.urheart.app/slot_1.webp');

      // CRITICAL ADVERSARIAL VERIFICATION: Onboarding immutable fields MUST NOT be submitted
      expect(
        capturedBody!.containsKey('dob'),
        isFalse,
        reason: 'CRITICAL: "dob" is immutable statutory data (§9 DPDP Act) and MUST NOT be submitted in PUT edit payload',
      );
      expect(
        capturedBody!.containsKey('gender'),
        isFalse,
        reason: 'CRITICAL: "gender" is immutable onboarding identity and MUST NOT be submitted in PUT edit payload',
      );
      expect(
        capturedBody!.containsKey('contact_bridge_raw'),
        isFalse,
        reason: 'CRITICAL: "contact_bridge_raw" MUST NOT be submitted in PUT edit payload',
      );
      expect(
        capturedBody!.containsKey('contact_bridge_handle'),
        isFalse,
        reason: 'CRITICAL: "contact_bridge_handle" MUST NOT be submitted in basic PUT edit payload',
      );
      expect(
        capturedBody!.containsKey('contact_bridge_type'),
        isFalse,
        reason: 'CRITICAL: "contact_bridge_type" MUST NOT be submitted in basic PUT edit payload',
      );
      expect(
        capturedBody!.containsKey('voice_spark_url'),
        isFalse,
        reason: '"voice_spark_url" is not part of basic edit payload',
      );
    });

    test('In onboarding mode (isEditMode == false), POST /api/v1/profile/create IS called with dob, gender, and contact_bridge_raw', () async {
      Uri? capturedUri;
      Map<String, dynamic>? capturedBody;
      bool profilePutCalled = false;

      mockHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/profile/create') {
          capturedUri = url;
          if (body != null) {
            capturedBody = jsonDecode(body.toString()) as Map<String, dynamic>;
          }
          return http.Response(
            jsonEncode({
              'success': true,
              'data': {'id': 'user-new', 'is_profile_completed': true},
            }),
            200,
          );
        }
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

      mockHttp.onPut = (url, headers, body) async {
        if (url.path == '/api/v1/profile') {
          profilePutCalled = true;
        }
        return http.Response('{}', 200);
      };

      await sessionStorage.writeCustomKey('user_dob', '1995-12-01');

      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: mockHttp,
        storage: sessionStorage,
      );

      // Verify default isEditMode is false
      expect(controller.state.isEditMode, isFalse);

      controller.updateTextFields(
        fullName: 'Rohan Mehra',
        bio: 'Philosopher and urban hiker.',
        profession: 'Data Scientist',
        education: 'IIT Delhi',
        contactBridgeHandle: '+919811223344',
      );
      controller.setGender('Man');
      controller.setInterestedIn('Women');

      await controller.uploadPhotoSlot(1, [1, 2, 3]);

      final success = await controller.submitProfile();

      expect(success, isTrue);
      expect(profilePutCalled, isFalse, reason: 'PUT /api/v1/profile must NOT be called in onboarding mode');
      expect(capturedUri?.path, '/api/v1/profile/create');
      expect(capturedBody, isNotNull);

      // In onboarding mode, immutable onboarding fields MUST be present
      expect(capturedBody!['dob'], '1995-12-01');
      expect(capturedBody!['gender'], 'Man');
      expect(capturedBody!['contact_bridge_raw'], '+919811223344');
      expect(capturedBody!['contact_bridge_handle'], '+919811223344');
      expect(capturedBody!['contact_bridge_type'], 'whatsapp');
      expect(capturedBody!['full_name'], 'Rohan Mehra');

      // Verify completion marker in storage
      expect(await sessionStorage.readCustomKey('is_profile_completed'), 'true');
    });

    test('Adversarial: Simulated network failure during submitProfile (edit mode) safely populates errorMessage without rethrowing', () async {
      mockHttp.onPut = (url, headers, body) async {
        throw http.ClientException('Network socket disconnected during PUT');
      };

      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: mockHttp,
        storage: sessionStorage,
      );

      controller.initializeForEdit(profileData: {
        'full_name': 'Test User',
        'photos': ['https://media.urheart.app/slot_1.webp'],
      });

      bool? result;
      expect(() async {
        result = await controller.submitProfile();
      }, returnsNormally);

      await Future<void>.delayed(const Duration(milliseconds: 10));

      expect(result, isFalse);
      expect(controller.state.isSubmitting, isFalse);
      expect(controller.state.errorMessage, isNotNull);
      expect(controller.state.errorMessage, contains('Network socket disconnected'));
    });

    test('Adversarial: Backend HTTP 400 (PROFILE_ALREADY_COMPLETED / VALIDATION_ERROR) populates state.errorMessage cleanly', () async {
      mockHttp.onPut = (url, headers, body) async {
        return http.Response(
          jsonEncode({
            'error_code': 'VALIDATION_ERROR',
            'message': 'Bio contains prohibited contact patterns.',
          }),
          400,
          headers: {'Content-Type': 'application/json'},
        );
      };

      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: mockHttp,
        storage: sessionStorage,
      );

      controller.initializeForEdit(profileData: {
        'full_name': 'Test User',
        'photos': ['https://media.urheart.app/slot_1.webp'],
      });

      final result = await controller.submitProfile();

      expect(result, isFalse);
      expect(controller.state.isSubmitting, isFalse);
      expect(controller.state.errorMessage, 'Bio contains prohibited contact patterns.');
    });

    test('Adversarial: Presigned URL acquisition network failure in media upload sets errorMessage and resets isUploadingMedia', () async {
      mockHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/media/presigned-url') {
          return http.Response(
            jsonEncode({
              'error_code': 'STORAGE_RATE_LIMIT_EXCEEDED',
              'message': 'Media storage quota rate limit exceeded.',
            }),
            429,
            headers: {'Content-Type': 'application/json'},
          );
        }
        return http.Response('{}', 200);
      };

      final controller = ProfileSetupController(
        client: client,
        rawHttpClient: mockHttp,
        storage: sessionStorage,
      );

      final success = await controller.uploadPhotoSlot(1, [0x01, 0x02]);

      expect(success, isFalse);
      expect(controller.state.isUploadingMedia, isFalse);
      expect(controller.state.errorMessage, 'Media storage quota rate limit exceeded.');
    });
  });
}
