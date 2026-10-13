import 'package:flutter/material.dart';

/// Typography hierarchy and optical contrast shielding for frosted-glass surfaces.
class SanctuaryTypography {
  static const String serifFont = 'PlayfairDisplay';
  static const String sansFont = 'PlusJakartaSans';

  /// Subtle dark-mode drop shadow to protect editorial text contrast over translucent glass.
  static const List<Shadow> glassTextShadow = [
    Shadow(
      offset: Offset(0, 1.5),
      blurRadius: 4.0,
      color: Color(0x66000000),
    ),
  ];

  /// Soft light-mode drop shadow protecting text contrast over milk-glass surfaces.
  static const List<Shadow> lightGlassTextShadow = [
    Shadow(
      offset: Offset(0, 1.0),
      blurRadius: 2.0,
      color: Color(0x1F000000),
    ),
  ];

  // Editorial Serif Hierarchy
  static TextStyle titleH1(Color color, {bool isDark = true}) => TextStyle(
        fontFamily: serifFont,
        fontSize: 32.0,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.5,
        height: 1.15,
        color: color,
        shadows: isDark ? glassTextShadow : lightGlassTextShadow,
      );

  static TextStyle titleH1Italic(Color color, {bool isDark = true}) => TextStyle(
        fontFamily: serifFont,
        fontSize: 32.0,
        fontWeight: FontWeight.w400,
        fontStyle: FontStyle.italic,
        letterSpacing: -0.3,
        height: 1.15,
        color: color,
        shadows: isDark ? glassTextShadow : lightGlassTextShadow,
      );

  static TextStyle titleH2(Color color, {bool isDark = true}) => TextStyle(
        fontFamily: serifFont,
        fontSize: 24.0,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.3,
        height: 1.20,
        color: color,
        shadows: isDark ? glassTextShadow : lightGlassTextShadow,
      );

  static TextStyle quote(Color color, {bool isDark = true}) => TextStyle(
        fontFamily: serifFont,
        fontSize: 18.0,
        fontWeight: FontWeight.w400,
        fontStyle: FontStyle.italic,
        letterSpacing: -0.2,
        height: 1.35,
        color: color,
        shadows: isDark ? glassTextShadow : lightGlassTextShadow,
      );

  // Modern Clean Sans-Serif Hierarchy
  static TextStyle bodyStandard(Color color) => TextStyle(
        fontFamily: sansFont,
        fontSize: 14.5,
        fontWeight: FontWeight.w400,
        height: 1.45,
        color: color,
      );

  static TextStyle bodyMedium(Color color) => TextStyle(
        fontFamily: sansFont,
        fontSize: 14.5,
        fontWeight: FontWeight.w500,
        height: 1.45,
        color: color,
      );

  static TextStyle bodySmall(Color color) => TextStyle(
        fontFamily: sansFont,
        fontSize: 12.5,
        fontWeight: FontWeight.w400,
        height: 1.40,
        color: color,
      );

  static TextStyle buttonPrimary(Color color) => TextStyle(
        fontFamily: sansFont,
        fontSize: 16.0,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.2,
        color: color,
      );

  static TextStyle caption(Color color) => TextStyle(
        fontFamily: sansFont,
        fontSize: 11.5,
        fontWeight: FontWeight.w500,
        letterSpacing: 0.4,
        color: color,
      );
}
