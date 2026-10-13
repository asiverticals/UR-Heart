import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ur_heart/core/services/window_security_service.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';

/// In-memory fake storage replacing platform channel implementation during unit testing.
class FakeSecureStorage extends Fake implements FlutterSecureStorage {
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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('WindowSecurityService Policy Tests', () {
    final List<MethodCall> methodCalls = [];

    setUp(() {
      methodCalls.clear();
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
        WindowSecurityService.channel,
        (MethodCall call) async {
          methodCalls.add(call);
          if (call.method == 'enableSecureWindow' || call.method == 'disableSecureWindow') {
            return true;
          }
          return null;
        },
      );
    });

    tearDown(() {
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(WindowSecurityService.channel, null);
    });

    test('Test 1: WindowSecurityService.isBypassedUser() permanently evaluates to false', () {
      expect(WindowSecurityService.isBypassedUser(), isFalse);
    });

    test('Test 2: WindowSecurityService.enforceWindowProtection() dispatches MethodChannel calls for sensitive routes', () async {
      // Sensitive route triggers enableSecureWindow
      await WindowSecurityService.enforceWindowProtection('/chat-dialogue');
      expect(methodCalls.map((c) => c.method), contains('enableSecureWindow'));

      methodCalls.clear();
      // Non-sensitive route does NOT trigger enableSecureWindow
      await WindowSecurityService.enforceWindowProtection('/settings');
      expect(methodCalls, isEmpty);

      // Sensitive vault route triggers enableSecureWindow
      await WindowSecurityService.enforceWindowProtection('/vault');
      expect(methodCalls.map((c) => c.method), contains('enableSecureWindow'));

      methodCalls.clear();
      // Relaxing window protection triggers disableSecureWindow
      await WindowSecurityService.relaxWindowProtection();
      expect(methodCalls.map((c) => c.method), contains('disableSecureWindow'));
    });
  });

  group('SecureSessionStorage Keystore Vault Tests', () {
    late FakeSecureStorage fakeStorage;
    late SecureSessionStorage sessionStorage;

    setUp(() {
      fakeStorage = FakeSecureStorage();
      sessionStorage = SecureSessionStorage(storage: fakeStorage);
    });

    tearDown(() {
      sessionStorage.dispose();
    });

    test('Test 3: SecureSessionStorage persists, reads tokens, and clears records upon logout', () async {
      expect(await sessionStorage.readAuthToken(), isNull);

      await sessionStorage.persistSession(
        accessToken: 'access_jwt_token_123',
        refreshToken: 'refresh_jwt_token_456',
        userId: 'usr_uuid_789',
        role: 'user',
      );

      expect(await sessionStorage.readAuthToken(), equals('access_jwt_token_123'));
      expect(await sessionStorage.readRefreshToken(), equals('refresh_jwt_token_456'));
      expect(await sessionStorage.readUserId(), equals('usr_uuid_789'));
      expect(await sessionStorage.readUserRole(), equals('user'));

      await sessionStorage.clearSession();

      expect(await sessionStorage.readAuthToken(), isNull);
      expect(await sessionStorage.readRefreshToken(), isNull);
      expect(await sessionStorage.readUserId(), isNull);
      expect(await sessionStorage.readUserRole(), isNull);
    });

    test('Test 4: watchAuthenticationState() correctly broadcasts session changes', () async {
      final emittedStates = <bool>[];
      final subscription = sessionStorage.watchAuthenticationState().listen((state) {
        emittedStates.add(state);
      });

      // Allow initial stream yield
      await Future<void>.delayed(const Duration(milliseconds: 10));

      await sessionStorage.persistSession(
        accessToken: 'new_access_token',
        refreshToken: 'new_refresh_token',
        userId: 'new_user_id',
        role: 'user',
      );

      await Future<void>.delayed(const Duration(milliseconds: 10));

      await sessionStorage.clearSession();

      await Future<void>.delayed(const Duration(milliseconds: 10));
      await subscription.cancel();

      // Expect sequence: initial false -> true (login) -> false (logout)
      expect(emittedStates, equals([false, true, false]));
    });

    test('Test 5: Concurrent persistSession and clearSession are serialized by FIFO queue', () async {
      // Launch persistSession and clearSession concurrently
      final f1 = sessionStorage.persistSession(
        accessToken: 'concurrent_token',
        refreshToken: 'concurrent_refresh',
        userId: 'concurrent_user',
        role: 'user',
      );
      final f2 = sessionStorage.clearSession();

      await Future.wait([f1, f2]);

      // Since clearSession was enqueued second, final state must be cleared
      expect(await sessionStorage.readAuthToken(), isNull);
      expect(await sessionStorage.readRefreshToken(), isNull);
      expect(await sessionStorage.readUserId(), isNull);
      expect(await sessionStorage.readUserRole(), isNull);
    });

    test('Test 6: watchAuthenticationState() subscribes before initial read', () async {
      final emittedStates = <bool>[];
      // Subscribe to stream
      final subscription = sessionStorage.watchAuthenticationState().listen((state) {
        emittedStates.add(state);
      });

      // Concurrently persist without waiting for initial read to finish
      await sessionStorage.persistSession(
        accessToken: 'fast_token',
        refreshToken: 'fast_refresh',
        userId: 'fast_user',
        role: 'user',
      );

      await Future<void>.delayed(const Duration(milliseconds: 20));
      await subscription.cancel();

      // Ensure that true state was delivered
      expect(emittedStates, contains(true));
    });
  });
}
