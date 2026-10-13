import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// Window protection service enforcing native Android hardware FLAG_SECURE and best-effort web keyboard event mitigations.
class WindowSecurityService {
  static const MethodChannel channel = MethodChannel('com.urheart.app/window_security');

  /// Set of viewports requiring strict hardware screenshot & recording prevention.
  static const Set<String> sensitiveRoutes = {
    '/chat-dialogue',
    '/main',
    '/seeker-detail',
    '/blind-date-session',
    '/vault',
  };

  /// Non-Negotiable Invariant: Administrative bypass is strictly impossible.
  /// Hardcoded to permanently return false to prohibit bypass of veiled photos or encrypted dialogue.
  static bool isBypassedUser() => false;

  /// Enforces FLAG_SECURE hardware protection on Android for declared sensitive routes.
  static Future<void> enforceWindowProtection(String currentRoute) async {
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      if (sensitiveRoutes.contains(currentRoute)) {
        try {
          await channel.invokeMethod<bool>('enableSecureWindow');
        } on PlatformException catch (_) {
          // Channel fallback/ignored in non-native or testing environments
        }
      }
    }
  }

  /// Relaxes window protection when navigating out of sensitive viewports.
  static Future<void> relaxWindowProtection() async {
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      try {
        await channel.invokeMethod<bool>('disableSecureWindow');
      } on PlatformException catch (_) {
        // Channel fallback/ignored in non-native or testing environments
      }
    }
  }

  /// Best-effort client-side web shortcut handler: intercepts PrintScreen key events
  /// to clear clipboard text and suppresses browser print/save shortcuts.
  ///
  /// Note: Browser sandboxes cannot prevent OS-level screen capture or recording tools.
  /// This handler provides client-side keyboard event interception within web platform limits.
  static void initializeWebProtection() {
    if (kIsWeb) {
      HardwareKeyboard.instance.addHandler(_handleWebKeyEvent);
    }
  }

  static bool _handleWebKeyEvent(KeyEvent event) {
    if (!kIsWeb) return false;

    // Best-effort mitigation: wipe clipboard on PrintScreen key event.
    // Note: This does not and cannot prevent OS-level screen capture in a browser.
    if (event.logicalKey == LogicalKeyboardKey.printScreen) {
      Clipboard.setData(const ClipboardData(text: ''));
      return true;
    }

    // Intercept Ctrl+P / Cmd+P (Print) and Ctrl+S / Cmd+S (Save)
    final isControlOrMeta = HardwareKeyboard.instance.isControlPressed ||
        HardwareKeyboard.instance.isMetaPressed;

    if (isControlOrMeta &&
        (event.logicalKey == LogicalKeyboardKey.keyP ||
            event.logicalKey == LogicalKeyboardKey.keyS)) {
      return true; // Consume event to suppress browser default action
    }

    return false;
  }
}
