import 'dart:math' as math;
import 'package:flutter/material.dart';

import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

/// Circular frosted progress display visualizing the 24-hour Mindful Streak countdown.
class StreakGaugeWidget extends StatelessWidget {
  final int streakCount;
  final int remainingSeconds;
  final double size;
  final VoidCallback? onTap;

  static const int totalStreakSeconds = 24 * 3600; // 86,400s

  const StreakGaugeWidget({
    super.key,
    required this.streakCount,
    required this.remainingSeconds,
    this.size = 170.0,
    this.onTap,
  });

  double get progressFraction {
    if (remainingSeconds <= 0) return 0.0;
    return (remainingSeconds / totalStreakSeconds).clamp(0.0, 1.0);
  }

  int get remainingHours => (remainingSeconds / 3600).floor();
  int get remainingMinutes => ((remainingSeconds % 3600) / 60).floor();

  String get remainingLabel {
    if (remainingSeconds <= 0) {
      return 'Conscious Rhythm';
    }
    if (remainingHours > 0) {
      return '${remainingHours}h Left';
    }
    if (remainingMinutes > 0) {
      return '${remainingMinutes}m Left';
    }
    return '<1m Left';
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return GestureDetector(
      onTap: onTap,
      child: SanctuaryGlassContainer(
        borderRadius: size / 2,
        blurSigma: 16.0,
        padding: const EdgeInsets.all(12.0),
        child: SizedBox(
          width: size,
          height: size,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Optical Gold Animated Arc Ring
              CustomPaint(
                size: Size(size, size),
                painter: _StreakArcPainter(
                  progress: progressFraction,
                  trackColor: tokens.borderSpecularStart.withValues(alpha: 0.25),
                  arcColor: SanctuaryGlassTokens.brandSacredGold,
                  strokeWidth: 6.0,
                ),
              ),

              // Central Streak Status Content
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Warm Flame Icon
                  Container(
                    padding: const EdgeInsets.all(8.0),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.18),
                      border: Border.all(
                        color: SanctuaryGlassTokens.brandTerracottaGlow.withValues(alpha: 0.4),
                      ),
                    ),
                    child: const Icon(
                      Icons.local_fire_department_rounded,
                      size: 22.0,
                      color: SanctuaryGlassTokens.brandTerracottaGlow,
                    ),
                  ),
                  const SizedBox(height: 6.0),

                  // Streak Count Text
                  Text(
                    '$streakCount Days',
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.serifFont,
                      fontSize: 18.0,
                      fontWeight: FontWeight.w700,
                      color: tokens.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2.0),

                  // Rhythm Sub-label
                  Text(
                    remainingLabel,
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.sansFont,
                      fontSize: 11.0,
                      fontWeight: FontWeight.w500,
                      color: tokens.textSecondary,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StreakArcPainter extends CustomPainter {
  final double progress;
  final Color trackColor;
  final Color arcColor;
  final double strokeWidth;

  _StreakArcPainter({
    required this.progress,
    required this.trackColor,
    required this.arcColor,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;

    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final arcPaint = Paint()
      ..color = arcColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    // Draw full background circular track
    canvas.drawCircle(center, radius, trackPaint);

    // Draw active countdown arc starting from top (-pi / 2)
    const startAngle = -math.pi / 2;
    final sweepAngle = 2 * math.pi * progress;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      arcPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _StreakArcPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.arcColor != arcColor ||
        oldDelegate.trackColor != trackColor;
  }
}
