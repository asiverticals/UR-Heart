import 'package:flutter/material.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

/// Non-dismissible statutory lockout dialog enforcing strict 18+ boundary.
/// Triggered when an underage birthdate is submitted or a quarantined device is intercepted.
class UnderageQuarantineDialog extends StatelessWidget {
  final DateTime? quarantineUntil;

  const UnderageQuarantineDialog({
    super.key,
    this.quarantineUntil,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    final remainingDays = quarantineUntil != null
        ? quarantineUntil!.difference(DateTime.now()).inDays.clamp(0, 365)
        : 180;

    return PopScope(
      canPop: false,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: SanctuaryGlassContainer(
            blurSigma: 24.0, // Tier 3 Modal Glass
            borderRadius: 24.0,
            borderWidth: 1.5,
            customBorderGradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                SanctuaryGlassTokens.alertRed,
                SanctuaryGlassTokens.alertRed.withValues(alpha: 0.2),
              ],
            ),
            padding: const EdgeInsets.all(28.0),
            child: Material(
              color: Colors.transparent,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.15),
                      border: Border.all(
                        color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.4),
                        width: 1.5,
                      ),
                    ),
                    child: const Icon(
                      Icons.gavel_rounded,
                      size: 32,
                      color: SanctuaryGlassTokens.alertRed,
                    ),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    'Sacred Boundary Enforced',
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.serifFont,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: tokens.textPrimary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'UR-Heart Sanctuary is strictly reserved for conscious seekers aged 18 and older. Under the Protection of Children from Sexual Offences (POCSO) Act 2012 and India DPDP Act 2023, access for minors is categorically prohibited.',
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.sansFont,
                      fontSize: 13,
                      height: 1.5,
                      color: tokens.textSecondary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 20),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.1),
                      border: Border.all(
                        color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.3),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.lock_clock_rounded,
                          size: 18,
                          color: SanctuaryGlassTokens.alertRed,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Hardware Lockout: $remainingDays Days Remaining',
                          style: const TextStyle(
                            fontFamily: SanctuaryTypography.sansFont,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: SanctuaryGlassTokens.alertRed,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Underage registration attempts are recorded and quarantined under statutory child safety mandates.',
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.sansFont,
                      fontSize: 11,
                      fontStyle: FontStyle.italic,
                      color: tokens.textTertiary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
