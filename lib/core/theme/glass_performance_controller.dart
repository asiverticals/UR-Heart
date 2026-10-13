import 'package:flutter/foundation.dart';

/// Performance guardrail for low-end GPUs and non-accelerated Web contexts.
class GlassPerformanceController {
  static bool enableLiveBackdropFilter = true;

  /// Call during app initialization (detect low-end devices or Web fallback).
  static void initializePerformanceSettings({bool isLowEndDevice = false}) {
    if (kIsWeb) {
      enableLiveBackdropFilter = !isLowEndDevice;
    } else if (isLowEndDevice) {
      enableLiveBackdropFilter = false;
    }
  }

  /// Resolves effective Gaussian blur sigma; returns 0.0 if live backdrop filtering is disabled.
  static double resolveSigma(double requestedSigma) {
    return enableLiveBackdropFilter ? requestedSigma : 0.0;
  }
}
