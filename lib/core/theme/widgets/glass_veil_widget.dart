import 'dart:ui';
import 'package:flutter/material.dart';
import '../glass_tokens.dart';
import '../glass_performance_controller.dart';
import '../../constants/app_typography.dart';

/// The 35px progressive revelation blur veil for Stage 1 modesty and privacy protection.
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
    final resolvedSigma = GlassPerformanceController.resolveSigma(veilBlur);

    return Stack(
      fit: StackFit.expand,
      children: [
        // Raw image underneath
        underlyingImage,

        // 35px Frosted Gaussian Veil or Opaque Privacy Fallback if blur below privacy threshold
        if (resolvedSigma < 20.0)
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
                sigmaX: resolvedSigma,
                sigmaY: resolvedSigma,
              ),
              child: Container(
                color: isDark ? Colors.black.withValues(alpha: 0.35) : Colors.white.withValues(alpha: 0.40),
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
                tokens.glowGold.withValues(alpha: 0.20),
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
                  child: const Icon(
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
                    fontFamily: SanctuaryTypography.serifFont,
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
                    fontFamily: SanctuaryTypography.sansFont,
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
                      backgroundColor: SanctuaryGlassTokens.brandPine.withValues(alpha: 0.85),
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
