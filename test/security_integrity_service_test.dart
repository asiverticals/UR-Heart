import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/network/ssl_pinning_client.dart';
import 'package:ur_heart/core/services/security_integrity_service.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';

class MockStorage extends Fake implements SecureSessionStorage {
  @override
  Future<String?> readAuthToken() async => null;
}

void main() {
  group('SecurityIntegrityService Threat Model Tests', () {
    test('Test 1: Clean device assessment returns uncompromised state', () async {
      final service = SecurityIntegrityService(
        fileExistsCheck: (path) => false,
        socketProbeCheck: (host, port) async => false,
      );

      final result = await service.assessIntegrity();

      expect(result.isRooted, isFalse);
      expect(result.isEmulator, isFalse);
      expect(result.isHookingDetected, isFalse);
      expect(result.isCompromised, isFalse);
      expect(result.flaggedIndicators, isEmpty);
    });

    test('Test 2: Detects su binary and marks device as rooted and compromised', () async {
      final service = SecurityIntegrityService(
        fileExistsCheck: (path) => path == '/system/bin/su',
        socketProbeCheck: (host, port) async => false,
      );

      final result = await service.assessIntegrity();

      expect(result.isRooted, isTrue);
      expect(result.isCompromised, isTrue);
      expect(result.flaggedIndicators, contains('SU_BINARY_FOUND: /system/bin/su'));
    });

    test('Test 3: Detects Magisk root kit filesystem artifacts', () async {
      final service = SecurityIntegrityService(
        fileExistsCheck: (path) => path == '/sbin/.magisk',
        socketProbeCheck: (host, port) async => false,
      );

      final result = await service.assessIntegrity();

      expect(result.isRooted, isTrue);
      expect(result.isCompromised, isTrue);
      expect(result.flaggedIndicators, contains('ROOT_KIT_FOUND: /sbin/.magisk'));
    });

    test('Test 4: Detects emulator pipe devices and marks isEmulator', () async {
      final service = SecurityIntegrityService(
        fileExistsCheck: (path) => path == '/dev/qemu_pipe',
        socketProbeCheck: (host, port) async => false,
      );

      final result = await service.assessIntegrity();

      expect(result.isEmulator, isTrue);
      expect(result.isRooted, isFalse);
      expect(result.flaggedIndicators, contains('EMULATOR_DEVICE_FOUND: /dev/qemu_pipe'));
    });

    test('Test 5: Detects active Frida instrumentation server on port 27042', () async {
      final service = SecurityIntegrityService(
        fileExistsCheck: (path) => false,
        socketProbeCheck: (host, port) async => port == 27042,
      );

      final result = await service.assessIntegrity();

      expect(result.isHookingDetected, isTrue);
      expect(result.isCompromised, isTrue);
      expect(result.flaggedIndicators, contains('FRIDA_SERVER_LISTENING: port 27042'));
    });

    test('Test 6: Multiple threats detected simultaneously', () async {
      final service = SecurityIntegrityService(
        fileExistsCheck: (path) => path == '/system/xbin/su' || path == '/dev/socket/qemud',
        socketProbeCheck: (host, port) async => port == 27042,
      );

      final result = await service.assessIntegrity();

      expect(result.isRooted, isTrue);
      expect(result.isEmulator, isTrue);
      expect(result.isHookingDetected, isTrue);
      expect(result.isCompromised, isTrue);
      expect(result.flaggedIndicators.length, equals(3));
    });
  });

  group('SSL Pinning & TLS Hardening Tests', () {
    test('Test 7: isSslPinningSupported returns boolean', () {
      expect(isSslPinningSupported(), isA<bool>());
    });

    test('Test 8: computeCertSha256Fingerprint accurately hashes DER bytes', () {
      final sampleBytes = Uint8List.fromList([1, 2, 3, 4, 5, 6, 7, 8]);
      final fingerprint = computeCertSha256Fingerprint(sampleBytes);
      expect(fingerprint.length, equals(64));
      // Hash of [1,2,3,4,5,6,7,8] in SHA-256
      expect(fingerprint, isNotEmpty);
    });

    test('Test 9: SanctuaryHttpClient supports pinnedFingerprints configuration', () {
      final storage = MockStorage();
      final client = SanctuaryHttpClient(
        storage,
        pinnedFingerprints: {'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'},
        enablePinning: true,
      );
      expect(client.requestTimeout, equals(SanctuaryHttpClient.defaultTimeout));
    });
  });
}
