import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Riverpod provider for singleton secure session vault access.
final secureSessionStorageProvider = Provider<SecureSessionStorage>((ref) {
  return SecureSessionStorage();
});

/// Hardware Keystore Session Vault storing tokens under EncryptedSharedPreferences (Android Keystore AES-256 GCM).
class SecureSessionStorage {
  static const String keyAuthToken = 'ur_heart_auth_token';
  static const String keyRefreshToken = 'ur_heart_refresh_token';
  static const String keyUserRole = 'ur_heart_user_role';
  static const String keyUserId = 'ur_heart_user_id';

  final FlutterSecureStorage _storage;
  final StreamController<bool> _authController = StreamController<bool>.broadcast();

  SecureSessionStorage({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(
                encryptedSharedPreferences: true,
                resetOnError: true,
              ),
              iOptions: IOSOptions(
                accessibility: KeychainAccessibility.first_unlock,
              ),
            );

  Future<void> _lock = Future.value();

  Future<T> _synchronized<T>(Future<T> Function() action) {
    final prevLock = _lock;
    final completer = Completer<void>();
    _lock = completer.future;

    return prevLock.then((_) => action()).whenComplete(() {
      completer.complete();
    });
  }

  /// Broadcast stream tracking real-time login and logout session state transitions.
  /// Subscribes to the broadcast stream immediately before reading initial storage state
  /// so that concurrent updates occurring during initial resolution are never dropped.
  Stream<bool> watchAuthenticationState() {
    late final StreamController<bool> controller;
    StreamSubscription<bool>? sub;

    controller = StreamController<bool>(
      onListen: () {
        sub = _authController.stream.listen(
          (val) {
            if (!controller.isClosed) controller.add(val);
          },
          onError: (err) {
            if (!controller.isClosed) controller.addError(err);
          },
        );

        _synchronized(() async {
          try {
            final token = await _storage.read(key: keyAuthToken);
            if (!controller.isClosed) {
              controller.add(token != null && token.isNotEmpty);
            }
          } catch (e) {
            if (!controller.isClosed) {
              controller.addError(e);
            }
          }
        });
      },
      onCancel: () {
        sub?.cancel();
      },
    );

    return controller.stream.distinct();
  }

  /// Persists authentic session tokens and user identifiers to encrypted storage.
  /// Serialized through FIFO queue to prevent race conditions with concurrent clearSession calls.
  Future<void> persistSession({
    required String accessToken,
    required String refreshToken,
    required String userId,
    required String role,
  }) => _synchronized(() async {
    await _storage.write(key: keyAuthToken, value: accessToken);
    await _storage.write(key: keyRefreshToken, value: refreshToken);
    await _storage.write(key: keyUserId, value: userId);
    await _storage.write(key: keyUserRole, value: role);
    _authController.add(true);
  });

  /// Reads JWT Bearer access token.
  Future<String?> readAuthToken() => _storage.read(key: keyAuthToken);

  /// Reads long-lived refresh token.
  Future<String?> readRefreshToken() => _storage.read(key: keyRefreshToken);

  /// Reads authenticated seeker UUID.
  Future<String?> readUserId() => _storage.read(key: keyUserId);

  /// Reads seeker authorization role ('user', 'superadmin', etc.).
  Future<String?> readUserRole() => _storage.read(key: keyUserRole);

  /// Wipes all sensitive session tokens and notifies subscribers of logout.
  /// Serialized through FIFO queue to prevent race conditions with concurrent persistSession calls.
  Future<void> clearSession() => _synchronized(() async {
    await _storage.delete(key: keyAuthToken);
    await _storage.delete(key: keyRefreshToken);
    await _storage.delete(key: keyUserId);
    await _storage.delete(key: keyUserRole);
    _authController.add(false);
  });

  /// Closes the internal broadcast controller when disposed.
  void dispose() {
    _authController.close();
  }
}
