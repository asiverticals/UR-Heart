import 'dart:ui';
import 'package:flutter/material.dart';
import '../glass_tokens.dart';
import '../glass_performance_controller.dart';

/// Base frosted-glass container primitive with directional specular gradient border.
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
    final resolvedSigma = GlassPerformanceController.resolveSigma(blurSigma);

    Widget content = Container(
      width: width,
      height: height,
      margin: margin,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(borderRadius),
        boxShadow: shadows ?? [
          BoxShadow(
            color: isDark ? Colors.black.withValues(alpha: 0.25) : const Color(0xFFD7CDC3).withValues(alpha: 0.3),
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
            sigmaX: resolvedSigma,
            sigmaY: resolvedSigma,
          ),
          child: Container(
            padding: padding,
            decoration: BoxDecoration(
              color: effectiveTint,
              borderRadius: BorderRadius.circular(borderRadius),
              border: Border.all(
                width: borderWidth,
                color: Colors.transparent, // Handled by specular gradient overlay
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
