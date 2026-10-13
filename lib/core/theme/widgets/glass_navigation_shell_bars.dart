import 'dart:ui';
import 'package:flutter/material.dart';
import '../glass_tokens.dart';
import '../glass_performance_controller.dart';

/// Floating frosted AppBar with bottom specular stroke and transparent background.
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
    final resolvedSigma = GlassPerformanceController.resolveSigma(18.0);

    return ClipRRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(
          sigmaX: resolvedSigma,
          sigmaY: resolvedSigma,
        ),
        child: Container(
          decoration: BoxDecoration(
            color: tokens.glassTintSecondary,
            border: Border(
              bottom: BorderSide(
                color: tokens.borderSpecularStart.withValues(alpha: 0.5),
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

/// Floating frosted bottom navigation bar with terracotta glows and selection animations.
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
    final resolvedSigma = GlassPerformanceController.resolveSigma(20.0);

    return Padding(
      padding: const EdgeInsets.only(left: 16.0, right: 16.0, bottom: 20.0),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(32.0),
        child: BackdropFilter(
          filter: ImageFilter.blur(
            sigmaX: resolvedSigma,
            sigmaY: resolvedSigma,
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
                  color: isDark ? Colors.black.withValues(alpha: 0.35) : const Color(0xFFD7CDC3).withValues(alpha: 0.4),
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
                          ? Border.all(color: tokens.borderSpecularStart.withValues(alpha: 0.7), width: 0.8)
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
                          child: isSelected ? item.activeIcon : item.icon,
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
