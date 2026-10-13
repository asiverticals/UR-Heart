import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

@immutable
class ThemeState {
  final bool isDark;
  const ThemeState({required this.isDark});

  ThemeState copyWith({bool? isDark}) {
    return ThemeState(isDark: isDark ?? this.isDark);
  }
}

/// Riverpod state notifier managing Sanctuary's bi-thematic switching and persistence.
class ThemeController extends StateNotifier<ThemeState> {
  static const _prefKey = 'sanctuary_theme_dark_mode';
  bool _userChanged = false;

  ThemeController() : super(const ThemeState(isDark: true)) {
    _loadPreference();
  }

  Future<void> _loadPreference() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (_userChanged || !mounted) return;
      state = ThemeState(isDark: prefs.getBool(_prefKey) ?? true);
    } catch (_) {
      // Retain default dark mode on storage failure
    }
  }

  Future<void> toggleTheme() async {
    _userChanged = true;
    final nextMode = !state.isDark;
    state = state.copyWith(isDark: nextMode);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_prefKey, nextMode);
    } catch (_) {
      // Storage error fallback
    }
  }
}

/// Riverpod provider for Sanctuary theme state.
final themeProvider = StateNotifierProvider<ThemeController, ThemeState>((ref) {
  return ThemeController();
});
