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

  ThemeController() : super(const ThemeState(isDark: true)) {
    _loadPreference();
  }

  Future<void> _loadPreference() async {
    final prefs = await SharedPreferences.getInstance();
    final isDark = prefs.getBool(_prefKey) ?? true;
    state = ThemeState(isDark: isDark);
  }

  Future<void> toggleTheme() async {
    final nextMode = !state.isDark;
    state = state.copyWith(isDark: nextMode);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_prefKey, nextMode);
  }
}

/// Riverpod provider for Sanctuary theme state.
final themeProvider = StateNotifierProvider<ThemeController, ThemeState>((ref) {
  return ThemeController();
});
