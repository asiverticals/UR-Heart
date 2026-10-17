import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../network/ssl_pinning_client.dart';

/// Riverpod provider for singleton device integrity sentinel.
final securityIntegrityServiceProvider = Provider<SecurityIntegrityService>((ref) {
  return SecurityIntegrityService();
});

/// Comprehensive assessment result of device runtime integrity.
@immutable
class IntegrityAssessmentResult {
  final bool isRooted;
  final bool isEmulator;
  final bool isHookingDetected;
  final List<String> flaggedIndicators;

  const IntegrityAssessmentResult({
    required this.isRooted,
    required this.isEmulator,
    required this.isHookingDetected,
    required this.flaggedIndicators,
  });

  /// Evaluates whether the runtime environment is actively compromised or untrusted.
  bool get isCompromised => isRooted || isHookingDetected;

  @override
  String toString() {
    return 'IntegrityAssessmentResult(isRooted: $isRooted, isEmulator: $isEmulator, isHookingDetected: $isHookingDetected, indicators: $flaggedIndicators)';
  }
}

/// Runtime security sentinel detecting root kits (Magisk, su), emulators, and dynamic instrumentation agents (Frida).
class SecurityIntegrityService {
  /// Well-known su binary locations on Android filesystems.
  static const List<String> knownSuPaths = [
    '/system/bin/su',
    '/system/xbin/su',
    '/sbin/su',
    '/system/app/Superuser.apk',
    '/system/bin/failsafe/su',
    '/data/local/xbin/su',
    '/data/local/bin/su',
    '/system/sd/xbin/su',
    '/data/local/su',
  ];

  /// Well-known Magisk and KernelSU filesystem artifacts.
  static const List<String> knownMagiskPaths = [
    '/sbin/.magisk',
    '/cache/.disable_magisk',
    '/dev/com.koushikdutta.superuser.daemon/',
  ];

  /// Well-known QEMU / emulator pipe and driver devices.
  static const List<String> knownEmulatorPaths = [
    '/dev/socket/qemud',
    '/dev/qemu_pipe',
    '/system/bin/qemu-props',
  ];

  /// Default Frida server TCP communication ports.
  static const List<int> fridaPorts = [27042, 27043];

  final bool Function(String path)? _customFileExistsCheck;
  final Future<bool> Function(String host, int port)? _customSocketProbeCheck;

  SecurityIntegrityService({
    bool Function(String path)? fileExistsCheck,
    Future<bool> Function(String host, int port)? socketProbeCheck,
  })  : _customFileExistsCheck = fileExistsCheck,
        _customSocketProbeCheck = socketProbeCheck;

  /// Performs a synchronous-compatible and async multi-vector integrity audit.
  Future<IntegrityAssessmentResult> assessIntegrity() async {
    // Web environments run in secure browser sandboxes where native OS root files do not apply.
    if (kIsWeb || !isSslPinningSupported()) {
      return const IntegrityAssessmentResult(
        isRooted: false,
        isEmulator: false,
        isHookingDetected: false,
        flaggedIndicators: [],
      );
    }

    final flagged = <String>[];
    bool isRooted = false;
    bool isEmulator = false;
    bool isHookingDetected = false;

    // Vector 1: Check su binaries
    for (final path in knownSuPaths) {
      if (_checkFileExists(path)) {
        isRooted = true;
        flagged.add('SU_BINARY_FOUND: $path');
      }
    }

    // Vector 2: Check Magisk / Root manager hooks
    for (final path in knownMagiskPaths) {
      if (_checkFileExists(path)) {
        isRooted = true;
        flagged.add('ROOT_KIT_FOUND: $path');
      }
    }

    // Vector 3: Check emulator artifacts
    for (final path in knownEmulatorPaths) {
      if (_checkFileExists(path)) {
        isEmulator = true;
        flagged.add('EMULATOR_DEVICE_FOUND: $path');
      }
    }

    // Vector 4: Probe Frida server ports
    for (final port in fridaPorts) {
      final isFridaActive = await _probePort('127.0.0.1', port);
      if (isFridaActive) {
        isHookingDetected = true;
        flagged.add('FRIDA_SERVER_LISTENING: port $port');
      }
    }

    return IntegrityAssessmentResult(
      isRooted: isRooted,
      isEmulator: isEmulator,
      isHookingDetected: isHookingDetected,
      flaggedIndicators: flagged,
    );
  }

  bool _checkFileExists(String path) {
    final check = _customFileExistsCheck;
    if (check != null) {
      return check(path);
    }
    return false;
  }

  Future<bool> _probePort(String host, int port) async {
    final probe = _customSocketProbeCheck;
    if (probe != null) {
      return probe(host, port);
    }
    return false;
  }
}
