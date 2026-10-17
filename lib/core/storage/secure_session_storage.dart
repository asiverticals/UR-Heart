import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Riverpod provider for singleton secure session vault access.
final secureSessionStorageProvider = Provider<SecureSessionStorage>((ref) {
  final storage = SecureSessionStorage();
  ref.onDispose(storage.dispose);
  return storage;
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
  /// Automatically rolls back previously written keys if any subsequent key write fails.
  Future<void> persistSession({
    required String accessToken,
    required String refreshToken,
    required String userId,
    required String role,
  }) => _synchronized(() async {
    final writtenKeys = <String>[];
    try {
      await _storage.write(key: keyAuthToken, value: accessToken);
      writtenKeys.add(keyAuthToken);
      await _storage.write(key: keyRefreshToken, value: refreshToken);
      writtenKeys.add(keyRefreshToken);
      await _storage.write(key: keyUserId, value: userId);
      writtenKeys.add(keyUserId);
      await _storage.write(key: keyUserRole, value: role);
      writtenKeys.add(keyUserRole);
      if (!_authController.isClosed) _authController.add(true);
    } catch (e) {
      for (final key in writtenKeys) {
        try {
          await _storage.delete(key: key);
        } catch (_) {}
      }
      rethrow;
    }
  });

  /// Reads JWT Bearer access token serialized with pending writes.
  Future<String?> readAuthToken() =>
      _synchronized(() => _storage.read(key: keyAuthToken));

  /// Saves updated JWT Bearer access token serialized with pending writes.
  Future<void> saveAuthToken(String token) => _synchronized(() async {
    await _storage.write(key: keyAuthToken, value: token);
    if (!_authController.isClosed) _authController.add(true);
  });

  /// Reads long-lived refresh token serialized with pending writes.
  Future<String?> readRefreshToken() =>
      _synchronized(() => _storage.read(key: keyRefreshToken));

  /// Saves updated long-lived refresh token serialized with pending writes.
  Future<void> saveRefreshToken(String token) => _synchronized(() async {
    await _storage.write(key: keyRefreshToken, value: token);
  });

  /// Reads authenticated seeker UUID serialized with pending writes.
  Future<String?> readUserId() =>
      _synchronized(() => _storage.read(key: keyUserId));

  /// Reads seeker authorization role ('user', 'superadmin', etc.) serialized with pending writes.
  Future<String?> readUserRole() =>
      _synchronized(() => _storage.read(key: keyUserRole));

  /// Reads custom key value serialized with pending writes.
  Future<String?> readCustomKey(String key) =>
      _synchronized(() => _storage.read(key: key));

  /// Writes custom key value serialized with pending writes.
  Future<void> writeCustomKey(String key, String value) =>
      _synchronized(() => _storage.write(key: key, value: value));

  /// Deletes custom key serialized with pending writes.
  Future<void> deleteCustomKey(String key) =>
      _synchronized(() => _storage.delete(key: key));

  /// Wipes all sensitive session tokens and notifies subscribers of logout.
  /// Serialized through FIFO queue to prevent race conditions with concurrent persistSession calls.
  Future<void> clearSession() => _synchronized(() async {
    Object? firstError;
    var authTokenDeleted = false;
    for (final key in [keyAuthToken, keyRefreshToken, keyUserId, keyUserRole]) {
      try {
        await _storage.delete(key: key);
        if (key == keyAuthToken) {
          authTokenDeleted = true;
        }
      } catch (e) {
        firstError ??= e;
      }
    }
    if (authTokenDeleted && !_authController.isClosed) {
      _authController.add(false);
    }
    if (firstError != null) throw firstError;
  });

  /// Closes the internal broadcast controller when disposed.
  void dispose() {
    _authController.close();
  }
}
