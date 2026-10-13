import 'package:flutter/material.dart';

/// Optical glass tokens for UR-Heart Sanctuary bi-thematic system.
@immutable
class SanctuaryGlassTokens {
  final bool isDark;

  // Base Canvas
  final Color backgroundCanvas;
  final Color elevatedSurface;

  // Glass Tints
  final Color glassTintPrimary;
  final Color glassTintSecondary;
  final Color glassTintElevated;

  // Specular Border Colors
  final Color borderSpecularStart;
  final Color borderSpecularEnd;

  // Radiance Glows
  final Color glowPine;
  final Color glowTerracotta;
  final Color glowGold;

  // Text Colors
  final Color textPrimary;
  final Color textSecondary;
  final Color textTertiary;

  const SanctuaryGlassTokens._({
    required this.isDark,
    required this.backgroundCanvas,
    required this.elevatedSurface,
    required this.glassTintPrimary,
    required this.glassTintSecondary,
    required this.glassTintElevated,
    required this.borderSpecularStart,
    required this.borderSpecularEnd,
    required this.glowPine,
    required this.glowTerracotta,
    required this.glowGold,
    required this.textPrimary,
    required this.textSecondary,
    required this.textTertiary,
  });

  /// Dark Sanctuary Master Palette (Midnight obsidian #0F1115 base, 7% white glass tint).
  factory SanctuaryGlassTokens.dark() {
    return const SanctuaryGlassTokens._(
      isDark: true,
      backgroundCanvas: Color(0xFF0F1115),
      elevatedSurface: Color(0xFF181B20),
      glassTintPrimary: Color(0x12FFFFFF), // 7% White
      glassTintSecondary: Color(0xA6181B20), // 65% Slate
      glassTintElevated: Color(0x1FFFFFFF), // 12% White
      borderSpecularStart: Color(0x38FFFFFF), // 22% Specular White
      borderSpecularEnd: Color(0x0AFFFFFF), // 4% Subtle White
      glowPine: Color(0x592D5A43), // 35% Pine
      glowTerracotta: Color(0x4DC85A32), // 30% Terracotta
      glowGold: Color(0x4DD4AF37), // 30% Gold
      textPrimary: Color(0xFFFDFDFD),
      textSecondary: Color(0xFFB0B5C0),
      textTertiary: Color(0xFF8E95A5), // Meets WCAG AA >= 4.5:1
    );
  }

  /// Light Sanctuary Master Palette (Warm cream #F9F6F0 base, 65% white milk-glass tint).
  factory SanctuaryGlassTokens.light() {
    return const SanctuaryGlassTokens._(
      isDark: false,
      backgroundCanvas: Color(0xFFF9F6F0),
      elevatedSurface: Color(0xFFFFFFFF),
      glassTintPrimary: Color(0xA6FFFFFF), // 65% White
      glassTintSecondary: Color(0xD9F9F6F0), // 85% Warm Cream
      glassTintElevated: Color(0xE0FFFFFF), // 88% White
      borderSpecularStart: Color(0xF2FFFFFF), // 95% Pure Specular
      borderSpecularEnd: Color(0x59D7CDC3), // 35% Warm Beige
      glowPine: Color(0x1F2D5A43), // 12% Pine
      glowTerracotta: Color(0x1FC85A32), // 12% Terracotta
      glowGold: Color(0x26D4AF37), // 15% Gold
      textPrimary: Color(0xFF1A1D24),
      textSecondary: Color(0xFF525866),
      textTertiary: Color(0xFF5C6370), // Meets WCAG AA >= 4.5:1
    );
  }

  /// Linear Gradient for standard 1.0px Specular Border (topLeft to bottomRight).
  LinearGradient get specularBorderGradient => LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [borderSpecularStart, borderSpecularEnd],
        stops: const [0.0, 1.0],
      );

  // Universal Semantic Brand Accents
  static const Color brandPine = Color(0xFF2D5A43);
  static const Color brandTerracotta = Color(0xFFC85A32);
  static const Color brandTerracottaGlow = Color(0xFFD97746);
  static const Color brandSacredGold = Color(0xFFD4AF37);
  static const Color alertRed = Color(0xFFEF4444);
  static const Color onlineEmerald = Color(0xFF2EC4B6);
  static const Color tickCyan = Color(0xFF34B7F1);
}
