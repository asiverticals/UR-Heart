1. Visual Paradigm & Glassmorphism Principles
UR-Heart Sanctuary uses a Living Frosted-Glass (Glassmorphism) visual language. The interface avoids flat opaque panels, harsh contrast lines, and uninspired container boxes, using multi-layered optical refraction, dynamic backdrop diffusion, translucent gradient borders, and ambient light sources.
MD

+ 1

The UX flow, 19 screens, and layout geometry from the master architecture remain identical. This design system defines how every component is rendered through optical physics in both Dark Sanctuary and Light Sanctuary modes.
MD

+ 1

┌────────────────────────────────────────────────────────────────────────┐
│                        SPECULAR LIGHT EMITTER                          │
│               (Top-Left Ambient Light Vector @ 135°)                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │   1.0px Translucent Specular Gradient Stroke             │
       │   ┌──────────────────────────────────────────────────┐   │
       │   │  Frosted Glass Body Tint (Tint Color + Opacity)  │   │
       │   │  ┌────────────────────────────────────────────┐  │   │
       │   │  │  Optical Diffusion Layer (ImageFilter.blur)│  │   │
       │   │  │  Backdrop sigmaX: 12.0 – 35.0, sigmaY: ... │  │   │
       │   │  │  ┌──────────────────────────────────────┐  │  │   │
       │   │  │  │  Content Layer: Typography & Icons   │  │  │   │
       │   │  │  │  (Subtle drop-shadow contrast shield)│  │  │   │
       │   │  │  └──────────────────────────────────────┘  │  │   │
       │   │  └────────────────────────────────────────────┘  │   │
       │   └──────────────────────────────────────────────────┘   │
       └────────────────────────────┬─────────────────────────────┘
                                    │
                                    ▼
       ┌──────────────────────────────────────────────────────────┐
       │  Subsurface Ambient Occlusion Shadow                     │
       │  (Soft tinted shadow with zero harsh edges)              │
       └──────────────────────────────────────────────────────────┘
The 4 Pillars of Sanctuary Glassmorphism
Multi-Pass Backdrop Diffusion: Surfaces use BackdropFilter with Gaussian blur (ui.ImageFilter.blur) rather than simple alpha opacity, keeping underlying context softly visible while keeping foreground content readable.
MD

Directional Specular Strokes: Containers feature a continuous 1.0px (or 1.5px) border rendered with a directional linear gradient: strong translucency facing the top-left light source, fading to near-total transparency at the bottom-right.

Bi-Thematic Chromatic Calibration:

Dark Sanctuary: High contrast, deep midnight obsidian base, low opacity glass tints, and subtle neon/warm glows (Pine, Terracotta, Gold).
MD

Light Sanctuary: Warm cream base, high luminosity, high opacity milk-glass layers, and soft beige ambient occlusion to eliminate eye fatigue.
MD

Legibility Contrast Shields: Text elements over glass include optical drop shadows to prevent contrast loss when passing over dynamic photo or video content behind the blur veil.
MD

1. Complete Dual Palette Reference (Dark vs. Light)
2.1 Dark Sanctuary Master Palette
Engineered for intimate, late-night emotional sanctuary. Mitigates OLED battery draw while providing atmospheric depth.

Token Identifier Hex / RGBA Code Optical Role & Usage Matrix
darkBackground #0F1115 
Absolute background canvas behind all glass viewports.
MD

darkElevatedSurface #181B20 
Secondary fallback surface for non-blurred sub-layers.
MD

darkGlassTintPrimary rgba(255, 255, 255, 0.07) Standard glass card body tint (Cards, List rows).
darkGlassTintSecondary rgba(24, 27, 32, 0.65) High-density glass tint (Modals, Bottom Navigation, AppBars).
darkGlassTintElevated rgba(255, 255, 255, 0.12) Interactive glass tint (Tapped state, Active chips).
darkBorderSpecular rgba(255, 255, 255, 0.22) Top-left specular highlight on dark glass borders.
darkBorderTranslucent rgba(255, 255, 255, 0.04) Bottom-right ambient fade on dark glass borders.
darkGlowPine rgba(45, 90, 67, 0.35) 
Ambient radial glow for discovery resonances & verified states.
MD

darkGlowTerracotta rgba(200, 90, 50, 0.30) 
Ambient radial glow for active swipes, alerts, and streak tokens.
MD

darkGlowGold rgba(212, 175, 55, 0.30) 
Sovereign Store passes, micro-perks, and Sacred Bridge.
MD

darkTextPrimary #FDFDFD Editorial headlines, bold display titles, primary inputs.
darkTextSecondary #B0B5C0 Subtitles, timestamps, bio body text, inactive icons.
darkTextTertiary #8E95A5 Captions, legal disclaimers, disabled button states.
2.2 Light Sanctuary Master Palette
Engineered for daytime reflection. Employs a warm cream foundation to avoid sterile clinical whites.
MD

Token Identifier Hex / RGBA Code Optical Role & Usage Matrix
lightBackground #F9F6F0 
Warm cream primary canvas behind all light glass elements.
MD

lightElevatedSurface #FFFFFF 
Pure white structural surface base.
MD

lightGlassTintPrimary rgba(255, 255, 255, 0.65) Milk-glass card tint (Cards, Discovery deck overlays).
lightGlassTintSecondary rgba(249, 246, 240, 0.85) High-density light glass tint (Modals, Bottom Nav Shell).
lightGlassTintElevated rgba(255, 255, 255, 0.88) Interactive light glass tint (Button default, focused fields).
lightBorderSpecular rgba(255, 255, 255, 0.95) Crisp specular highlight border facing top-left.
lightBorderTranslucent rgba(215, 205, 195, 0.35) Soft warm border fade on bottom-right edges.
lightGlowPine rgba(45, 90, 67, 0.12) 
Subtle emerald radiance for mindful states.
MD

lightGlowTerracotta rgba(200, 90, 50, 0.12) 
Warm terracotta morning glow.
MD

lightGlowGold rgba(212, 175, 55, 0.15) 
Sacred gold ambient reflection.
MD

lightTextPrimary #1A1D24 Primary high-contrast text on milk-glass surfaces.
lightTextSecondary #525866 Secondary body text, profile credentials, timestamps.
lightTextTertiary #5C6370 Footers, unselected items, helper hints.
2.3 Universal Accent & Brand Tokens
Constant semantic tokens used across both themes:

Sanctuary Pine: #2D5A43 (Brand Identity, Nature, Equilibrium)
MD

Warm Terracotta: #C85A32 (Human Connection, Passion, Sacred Action)
MD

Glowing Terracotta: #D97746 (Active Button State, Highlights)
MD

Sacred Gold: #D4AF37 (Sovereignty, Sacred Bridge, Premium Perks)
MD

Alert Red: #EF4444 (Account Incinerator, Harassment Report, Age Gate Block)
MD

Online Emerald: #2EC4B6 (Real-time Presence, WebSocket Active Indicator)
MD

Tick Cyan: #34B7F1 (Encrypted Read Receipts in Dialogue Chamber)
MD

1. Optical Physics, Blur Tiers & Shadow Tokens
To maintain visual hierarchy and prevent GPU bottlenecks, blur intensity and border treatments are categorized into five functional tiers:

┌────────────────────────────────────────────────────────────────────────┐
│                        GLASS OPTICAL HIERARCHY                         │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 0: Nano Glass (Chips, Badges, Pills) ───► sigma: 8.0, r: 8px      │
│ TIER 1: Standard Glass (Cards, Tiles, Rows) ─► sigma: 12.0, r: 16px    │
│ TIER 2: Deep Glass (AppBars, BottomNav) ─────► sigma: 18.0, r: 24px    │
│ TIER 3: Modal Glass (Dialogs, BottomSheets) ─► sigma: 24.0, r: 28px    │
│ TIER 4: Sanctuary Veil (35px Blur Shield) ───► sigma: 35.0, r: 20px    │
└────────────────────────────────────────────────────────────────────────┘
Optical Specification Matrix
Glass Tier Target Components Blur (sigmaX, sigmaY) Stroke Width Border Radii Ambient Shadow
Tier 0: Nano Streak Badges, KYC Pills, Verification Chips 8.0, 8.0 0.75px 8.0px – 12.0px None
Tier 1: Standard Discovery Cards, Chat Message Bubbles, Setting Rows 12.0, 12.0 1.0px 16.0px – 20.0px offset: (0, 8), blur: 24.0, opacity: 0.08
Tier 2: Deep GlassAppBar, GlassBottomNavBar, Floating Action Shell 18.0, 18.0 1.2px 24.0px – 32.0px offset: (0, 12), blur: 32.0, opacity: 0.15
Tier 3: Modal PassWithGraceDialog, Store Modals, Grievance Sheets 24.0, 24.0 1.5px 24.0px – 32.0px offset: (0, 16), blur: 48.0, opacity: 0.25
Tier 4: Veil Stage 1 Discovery Photo Blur, Blind Date Veiled Mirror 35.0, 35.0 1.5px 20.0px 
Inset glow: sacredGold.withOpacity(0.12)

MD

1. Typography Hierarchy & Optical Legibility on Glass
Translucent surfaces create varying background luminances. All typography uses high-contrast fonts (PlayfairDisplay and PlusJakartaSans) along with micro drop shadows to remain legible over blurred content.
MD

                                  ┌───────────────────────────────┐
                                  │      Playfair Display         │
                                  │   (Editorial Serif Titles)    │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │      Plus Jakarta Sans        │
                                  │ (Legible UI, Body, Buttons)   │
                                  └───────────────┬───────────────┘
                                                  │
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │    Optical Shadow Shield      │
                                  │ (Blur: 3.0, Color: 0x40000000)│
                                  └───────────────────────────────┘

MD

Typography Spec with Glass Contrast Rules
Dart

// lib/core/constants/app_typography.dart
import 'package:flutter/material.dart';

class SanctuaryTypography {
  static const String serifFont = 'PlayfairDisplay';
  static const String sansFont = 'PlusJakartaSans';

  // Subtle contrast drop shadow to protect legibility on glass
  static const List<Shadow> glassTextShadow = [
    Shadow(
      offset: Offset(0, 1.5),
      blurRadius: 4.0,
      color: Color(0x66000000),
    ),
  ];

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

MD

1. Production Dart Token Implementation (glass_tokens.dart)
Dart

// lib/core/theme/glass_tokens.dart
import 'package:flutter/material.dart';

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

  factory SanctuaryGlassTokens.dark() {
    return const SanctuaryGlassTokens._(
      isDark: true,
      backgroundCanvas: Color(0xFF0F1115),
      elevatedSurface: Color(0xFF181B20),
      glassTintPrimary: Color(0x12FFFFFF),       // 7% White
      glassTintSecondary: Color(0xA6181B20),     // 65% Slate
      glassTintElevated: Color(0x1FFFFFFF),      // 12% White
      borderSpecularStart: Color(0x38FFFFFF),    // 22% Specular White
      borderSpecularEnd: Color(0x0AFFFFFF),      // 4% Subtle White
      glowPine: Color(0x592D5A43),               // 35% Pine
      glowTerracotta: Color(0x4DC85A32),         // 30% Terracotta
      glowGold: Color(0x4DD4AF37),               // 30% Gold
      textPrimary: Color(0xFFFDFDFD),
      textSecondary: Color(0xFFB0B5C0),
      textTertiary: Color(0xFF8E95A5), // Meets WCAG AA >= 4.5:1 against dark canvas
    );
  }

  factory SanctuaryGlassTokens.light() {
    return const SanctuaryGlassTokens._(
      isDark: false,
      backgroundCanvas: Color(0xFFF9F6F0),
      elevatedSurface: Color(0xFFFFFFFF),
      glassTintPrimary: Color(0xA6FFFFFF),       // 65% White
      glassTintSecondary: Color(0xD9F9F6F0),     // 85% Warm Cream
      glassTintElevated: Color(0xE0FFFFFF),      // 88% White
      borderSpecularStart: Color(0xF2FFFFFF),    // 95% Pure Specular
      borderSpecularEnd: Color(0x59D7CDC3),      // 35% Warm Beige
      glowPine: Color(0x1F2D5A43),               // 12% Pine
      glowTerracotta: Color(0x1FC85A32),         // 12% Terracotta
      glowGold: Color(0x26D4AF37),               // 15% Gold
      textPrimary: Color(0xFF1A1D24),
      textSecondary: Color(0xFF525866),
      textTertiary: Color(0xFF5C6370), // Meets WCAG AA >= 4.5:1 against light canvas
    );
  }

  // Linear Gradient for standard 1px Specular Border
  LinearGradient get specularBorderGradient => LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [borderSpecularStart, borderSpecularEnd],
    stops: const [0.0, 1.0],
  );

  // Accent Colors
  static const Color brandPine = Color(0xFF2D5A43);
  static const Color brandTerracotta = Color(0xFFC85A32);
  static const Color brandTerracottaGlow = Color(0xFFD97746);
  static const Color brandSacredGold = Color(0xFFD4AF37);
  static const Color alertRed = Color(0xFFEF4444);
  static const Color onlineEmerald = Color(0xFF2EC4B6);
  static const Color tickCyan = Color(0xFF34B7F1);
}

MD

1. Core Reusable Flutter Glass Widgets
6.1 SanctuaryGlassContainer (Foundation Primitive)
The base building block for all frosted cards, dialog boxes, and inputs.

Dart

// lib/core/theme/widgets/sanctuary_glass_container.dart
import 'dart:ui';
import 'package:flutter/material.dart';
import '../glass_tokens.dart';
import '../glass_performance_controller.dart';

class SanctuaryGlassContainer extends StatelessWidget {
  final Widget child;
  final double? width;
  final double? height;
  final EdgeInsetsGeometry padding;
  final EdgeInsetsGeometry margin;
  final double borderRadius;
  final double blurSigma;
  final Color? customTint;
  final Gradient? customBorderGradient;
  final double borderWidth;
  final List<BoxShadow>? shadows;
  final VoidCallback? onTap;

  const SanctuaryGlassContainer({
    super.key,
    required this.child,
    this.width,
    this.height,
    this.padding = const EdgeInsets.all(16.0),
    this.margin = EdgeInsets.zero,
    this.borderRadius = 16.0,
    this.blurSigma = 12.0,
    this.customTint,
    this.customBorderGradient,
    this.borderWidth = 1.0,
    this.shadows,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();
    final effectiveTint = customTint ?? tokens.glassTintPrimary;
    final effectiveBorderGradient = customBorderGradient ?? tokens.specularBorderGradient;

    Widget content = Container(
      width: width,
      height: height,
      margin: margin,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(borderRadius),
        boxShadow: shadows ?? [
          BoxShadow(
            color: isDark ? Colors.black.withOpacity(0.25) : const Color(0xFFD7CDC3).withOpacity(0.3),
            offset: const Offset(0, 8),
            blurRadius: 24.0,
            spreadRadius: -4.0,
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(borderRadius),
        child: BackdropFilter(
          filter: ImageFilter.blur(
            sigmaX: GlassPerformanceController.resolveSigma(blurSigma),
            sigmaY: GlassPerformanceController.resolveSigma(blurSigma),
          ),
          child: Container(
            padding: padding,
            decoration: BoxDecoration(
              color: effectiveTint,
              borderRadius: BorderRadius.circular(borderRadius),
              border: Border.all(
                width: borderWidth,
                color: Colors.transparent, // Handled by gradient overlay below
              ),
            ),
            child: child,
          ),
        ),
      ),
    );

    // Apply specular gradient border painter on top of blurred child
    content = CustomPaint(
      foregroundPainter: _SpecularBorderPainter(
        radius: borderRadius,
        strokeWidth: borderWidth,
        gradient: effectiveBorderGradient,
      ),
      child: content,
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: content,
      );
    }
    return content;
  }
}

class _SpecularBorderPainter extends CustomPainter {
  final double radius;
  final double strokeWidth;
  final Gradient gradient;

  _SpecularBorderPainter({
    required this.radius,
    required this.strokeWidth,
    required this.gradient,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final rrect = RRect.fromRectAndRadius(rect, Radius.circular(radius));
    final paint = Paint()
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..shader = gradient.createShader(rect);

    canvas.drawRRect(rrect, paint);
  }

  @override
  bool shouldRepaint(covariant _SpecularBorderPainter oldDelegate) =>
      oldDelegate.radius != radius ||
      oldDelegate.strokeWidth != strokeWidth ||
      oldDelegate.gradient != gradient;
}
6.2 GlassVeilWidget (The 35px Progressive Revelation Shield)
Fulfills Stage 1 Sanctuary Discovery and Blind Date photo privacy requirements. Replaces flat pixelation with a frosted blur veil, specular edge lighting, and an optional resonance unmasking animation.
MD

+ 1

Dart

// lib/core/theme/widgets/glass_veil_widget.dart
import 'dart:ui';
import 'package:flutter/material.dart';
import '../glass_tokens.dart';
import '../glass_performance_controller.dart';
import '../../constants/app_typography.dart';

class GlassVeilWidget extends StatelessWidget {
  final Widget underlyingImage;
  final bool isVeiled;
  final VoidCallback? onConsentRequested;
  final String seekerFirstName;
  final double veilBlur;

  const GlassVeilWidget({
    super.key,
    required this.underlyingImage,
    required this.isVeiled,
    this.onConsentRequested,
    this.seekerFirstName = 'Seeker',
    this.veilBlur = 35.0, // Strict 35px Blur Veil standard
  });

  @override
  Widget build(BuildContext context) {
    if (!isVeiled) return underlyingImage;

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Stack(
      fit: StackFit.expand,
      children: [
        // Raw image underneath
        underlyingImage,

        // 35px Frosted Gaussian Veil or Opaque Privacy Fallback if backdrop filter disabled
        if (!GlassPerformanceController.enableLiveBackdropFilter)
          Container(
            color: isDark ? const Color(0xFF181B20) : const Color(0xFFF9F6F0),
            child: Center(
              child: Icon(
                Icons.visibility_off_rounded,
                size: 48,
                color: tokens.textSecondary,
              ),
            ),
          )
        else
          ClipRRect(
            child: BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: veilBlur,
                sigmaY: veilBlur,
              ),
              child: Container(
                color: isDark ? Colors.black.withOpacity(0.35) : Colors.white.withOpacity(0.40),
              ),
            ),
          ),

        // Ambient Gold Sacred Geometry Glow Overlay
        Container(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: Alignment.center,
              radius: 0.85,
              colors: [
                tokens.glowGold.withOpacity(0.20),
                Colors.transparent,
              ],
            ),
          ),
        ),

        // Veiled Privacy Indicator & Revelation Action Trigger
        Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.all(14.0),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: tokens.glassTintElevated,
                    border: Border.all(color: tokens.borderSpecularStart, width: 1.0),
                  ),
                  child: Icon(
                    Icons.remove_red_eye_outlined,
                    color: SanctuaryGlassTokens.brandSacredGold,
                    size: 28.0,
                  ),
                ),
                const SizedBox(height: 12.0),
                Text(
                  "Veiled in Sacred Modesty",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: 'PlayfairDisplay',
                    fontSize: 18.0,
                    fontWeight: FontWeight.w600,
                    color: tokens.textPrimary,
                    shadows: isDark
                        ? SanctuaryTypography.glassTextShadow
                        : SanctuaryTypography.lightGlassTextShadow,
                  ),
                ),
                const SizedBox(height: 6.0),
                Text(
                  "Photos reveal upon mutual resonance or bilateral consent.",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: 'PlusJakartaSans',
                    fontSize: 12.0,
                    fontWeight: FontWeight.w400,
                    color: tokens.textSecondary,
                  ),
                ),
                if (onConsentRequested != null) ...[
                  const SizedBox(height: 16.0),
                  ElevatedButton.icon(
                    onPressed: onConsentRequested,
                    icon: const Icon(Icons.auto_awesome, size: 16.0),
                    label: Text("Request Reveal to $seekerFirstName"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: SanctuaryGlassTokens.brandPine.withOpacity(0.85),
                      foregroundColor: Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20.0),
                        side: BorderSide(color: tokens.borderSpecularStart, width: 0.8),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 18.0, vertical: 10.0),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }
}

MD

6.3 GlassAppBar & GlassBottomNavBar
Floating frosted top and bottom application bars for SanctuaryNavigationShell.
MD

Dart

// lib/core/theme/widgets/glass_navigation_shell_bars.dart
import 'dart:ui';
import 'package:flutter/material.dart';
import '../glass_tokens.dart';
import '../glass_performance_controller.dart';

class GlassAppBar extends StatelessWidget implements PreferredSizeWidget {
  final Widget title;
  final List<Widget>? actions;
  final Widget? leading;
  final bool automaticallyImplyLeading;

  const GlassAppBar({
    super.key,
    required this.title,
    this.actions,
    this.leading,
    this.automaticallyImplyLeading = true,
  });

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight + 8.0);

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return ClipRRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(
          sigmaX: GlassPerformanceController.resolveSigma(18.0),
          sigmaY: GlassPerformanceController.resolveSigma(18.0),
        ),
        child: Container(
          decoration: BoxDecoration(
            color: tokens.glassTintSecondary,
            border: Border(
              bottom: BorderSide(
                color: tokens.borderSpecularStart.withOpacity(0.5),
                width: 1.0,
              ),
            ),
          ),
          child: AppBar(
            backgroundColor: Colors.transparent,
            elevation: 0,
            leading: leading,
            automaticallyImplyLeading: automaticallyImplyLeading,
            title: title,
            actions: actions,
            centerTitle: true,
          ),
        ),
      ),
    );
  }
}

class GlassBottomNavBar extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;
  final List<BottomNavigationBarItem> items;

  const GlassBottomNavBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
    required this.items,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Padding(
      padding: const EdgeInsets.only(left: 16.0, right: 16.0, bottom: 20.0),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(32.0),
        child: BackdropFilter(
          filter: ImageFilter.blur(
            sigmaX: GlassPerformanceController.resolveSigma(20.0),
            sigmaY: GlassPerformanceController.resolveSigma(20.0),
          ),
          child: Container(
            height: 68.0,
            decoration: BoxDecoration(
              color: tokens.glassTintSecondary,
              borderRadius: BorderRadius.circular(32.0),
              border: Border.all(
                color: tokens.borderSpecularStart,
                width: 1.2,
              ),
              boxShadow: [
                BoxShadow(
                  color: isDark ? Colors.black.withOpacity(0.35) : const Color(0xFFD7CDC3).withOpacity(0.4),
                  offset: const Offset(0, 10),
                  blurRadius: 30.0,
                ),
              ],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: List.generate(items.length, (index) {
                final isSelected = currentIndex == index;
                final item = items[index];
                return GestureDetector(
                  onTap: () => onTap(index),
                  behavior: HitTestBehavior.opaque,
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 250),
                    curve: Curves.easeOutCubic,
                    padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 8.0),
                    decoration: BoxDecoration(
                      color: isSelected
                          ? tokens.glassTintElevated
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(20.0),
                      border: isSelected
                          ? Border.all(color: tokens.borderSpecularStart.withOpacity(0.7), width: 0.8)
                          : null,
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconTheme(
                          data: IconThemeData(
                            color: isSelected
                                ? SanctuaryGlassTokens.brandTerracottaGlow
                                : tokens.textTertiary,
                            size: 24.0,
                          ),
                          child: isSelected ? (item.activeIcon ?? item.icon) : item.icon,
                        ),
                        const SizedBox(height: 2.0),
                        Text(
                          item.label ?? '',
                          style: TextStyle(
                            fontFamily: 'PlusJakartaSans',
                            fontSize: 10.5,
                            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                            color: isSelected
                                ? tokens.textPrimary
                                : tokens.textTertiary,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              }),
            ),
          ),
        ),
      ),
    );
  }
}

MD

1. Performance Guardrails (PWA & Low-End GPU Fallbacks)
Real-time Gaussian backdrop filters can strain low-end devices or browser contexts without WebGL acceleration. The rules below preserve 60fps performance across web browsers and budget devices:

7.1 Prevention of Nested Overdraw
The Single-Backdrop Rule: Do not nest a BackdropFilter inside another BackdropFilter viewport. For child elements within an already-blurred container (such as button chips inside a glass discovery card), use flat semi-transparent fills (tokens.glassTintElevated) without an extra ImageFilter.blur.

7.2 Low-End GPU Detection & Graceful Fallback
When a device drops frames or when running on the Flutter Web HTML renderer where backdrop blurs incur a performance cost:

Dart

// lib/core/theme/glass_performance_controller.dart
import 'package:flutter/foundation.dart';

class GlassPerformanceController {
  static bool enableLiveBackdropFilter = true;

  /// Call during app initialization (detect low-end devices or Web fallback)
  static void initializePerformanceSettings({bool isLowEndDevice = false}) {
    if (kIsWeb) {
      // In Flutter 3.29+, Web uses CanvasKit / Skwasm engines where shader blurs run hardware accelerated.
      enableLiveBackdropFilter = !isLowEndDevice;
    } else if (isLowEndDevice) {
      // Bypass costly blur computations, preserve opacity & border styling
      enableLiveBackdropFilter = false;
    }
  }

  static double resolveSigma(double requestedSigma) {
    return enableLiveBackdropFilter ? requestedSigma : 0.0;
  }
}
When enableLiveBackdropFilter is disabled:

resolveSigma() returns 0.0, eliminating Gaussian kernel GPU computations.

The UI keeps effectiveTint opacities and gradient borders intact, maintaining the glass aesthetic without rendering lag.

1. Verification & Acceptance Checklist
To confirm the glassmorphism system is correctly implemented in lib/:

[ ] SanctuaryGlassTokens.dark() matches background #0F1115 with 7% white tint and specular gradient.
MD

[ ] SanctuaryGlassTokens.light() matches background #F9F6F0 with 65% white milk-glass tint.
MD

[ ] All serif headlines use PlayfairDisplay with optical drop-shadow protection.
MD

[ ] All body text uses PlusJakartaSans with validated contrast over blurred surfaces.
MD

[ ] GlassVeilWidget implements the 35px blur veil for photo privacy.
MD

[ ] Floating navigation bars use GlassAppBar and GlassBottomNavBar.
MD

[ ] Nested BackdropFilter widgets are avoided on child components.

[ ] Static analysis passes cleanly: dart analyze lib reports zero warnings or errors.
MD
