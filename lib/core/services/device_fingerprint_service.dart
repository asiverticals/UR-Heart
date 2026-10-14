import 'dart:math';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../storage/secure_session_storage.dart';

/// Riverpod provider for singleton device fingerprint service.
final deviceFingerprintServiceProvider = Provider<DeviceFingerprintService>((ref) {
  final storage = ref.watch(secureSessionStorageProvider);
  return DeviceFingerprintService(storage);
});

/// Hardware anchor generating and retrieving persistent cryptographic device hashes.
/// Stored in hardware-backed EncryptedSharedPreferences / Keychain to survive app cache purges.
class DeviceFingerprintService {
  static const String keyDeviceFingerprint = 'ur_heart_device_fingerprint';
  final SecureSessionStorage _storage;

  DeviceFingerprintService(this._storage);

  Future<String>? _pending;

  /// Retrieves existing hardware fingerprint or generates a new 64-character cryptographic token.
  /// Caches the in-flight Future so concurrent first-launch callers share one result.
  Future<String> getOrCreateFingerprint() {
    return _pending ??= _loadOrCreate().whenComplete(() => _pending = null);
  }

  Future<String> _loadOrCreate() async {
    final storedFp = await _storage.readCustomKey(keyDeviceFingerprint);
    if (storedFp != null && storedFp.length == 64) {
      return storedFp;
    }

    final newFp = _generateHardwareHash();
    await _storage.writeCustomKey(keyDeviceFingerprint, newFp);
    return newFp;
  }

  /// Generates a 64-character cryptographic SHA-256 hardware anchor format.
  String _generateHardwareHash() {
    final random = Random.secure();
    final bytes = List<int>.generate(32, (_) => random.nextInt(256));
    return bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}
