import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/constants/app_typography.dart';
import '../../../../core/network/sanctuary_http_client.dart';
import '../../../../core/services/slumber_service.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

/// Tier 3 Modal Glass dialog presenting restorative slumber multiplier and morning harvest rewards.
class MorningHarvestDialog extends ConsumerStatefulWidget {
  final double sleepHours;
  final String? userId;
  final bool isVerified;
  final VoidCallback? onHarvestSuccess;

  const MorningHarvestDialog({
    super.key,
    required this.sleepHours,
    this.userId,
    this.isVerified = true,
    this.onHarvestSuccess,
  });

  static Future<bool?> show(
    BuildContext context, {
    required double sleepHours,
    String? userId,
    bool isVerified = true,
    VoidCallback? onHarvestSuccess,
  }) {
    return showDialog<bool>(
      context: context,
      barrierDismissible: true,
      barrierColor: Colors.black.withValues(alpha: 0.65),
      builder: (ctx) => MorningHarvestDialog(
        sleepHours: sleepHours,
        userId: userId,
        isVerified: isVerified,
        onHarvestSuccess: onHarvestSuccess,
      ),
    );
  }

  @override
  ConsumerState<MorningHarvestDialog> createState() => _MorningHarvestDialogState();
}

class _MorningHarvestDialogState extends ConsumerState<MorningHarvestDialog> {
  bool _isClaiming = false;
  String? _errorMessage;

  double get multiplier {
    if (!widget.isVerified) return 1.0;
    final clamped = widget.sleepHours.clamp(0.0, 12.0);
    if (clamped >= 8.0) return 2.0;
    if (clamped >= 6.0) return 1.5;
    return 1.0;
  }

  int get swipesAwarded => (10 * multiplier).toInt();
  int get boostPointsAwarded => multiplier == 2.0 ? 25 : (10 * multiplier).toInt();
  int get directLettersAwarded => multiplier == 2.0 ? 2 : 0;

  Future<void> _claimHarvest() async {
    setState(() {
      _isClaiming = true;
      _errorMessage = null;
    });

    try {
      final client = ref.read(sanctuaryHttpClientProvider);
      final clamped = widget.sleepHours.clamp(0.0, 12.0);
      final response = await client.post(
        '/api/v1/streak/claim-morning-harvest',
        body: {
          'sleep_duration_hours': clamped,
          'is_verified': widget.isVerified,
        },
      );

      // Mark locally claimed in SlumberService with account scoping
      await ref.read(slumberServiceProvider).markHarvestClaimed(userId: widget.userId);

      // Invoke callback unconditionally upon success, ensuring parent notification
      // even if dialog is unmounted or dismissed during the network operation
      widget.onHarvestSuccess?.call();

      if (!mounted) return;

      final messenger = ScaffoldMessenger.of(context);
      final message = response['data']?['message'] ?? response['message'] ?? 'Morning harvest blessed your sanctuary.';
      Navigator.of(context).pop(true);

      messenger.showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: SanctuaryGlassTokens.brandPine,
        ),
      );
    } on SanctuaryClientException catch (e) {
      if (!mounted) return;
      setState(() {
        _isClaiming = false;
        _errorMessage = e.message;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _isClaiming = false;
        _errorMessage = 'Failed to claim morning harvest. Please check connection.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return PopScope(
      canPop: !_isClaiming,
      child: Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
        child: SanctuaryGlassContainer(
          borderRadius: 28.0,
          blurSigma: 24.0, // Tier 3 Modal Glass
          padding: const EdgeInsets.all(28.0),
          child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Dawn Icon Emblem
            Center(
              child: Container(
                padding: const EdgeInsets.all(16.0),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
                  border: Border.all(
                    color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.4),
                    width: 1.2,
                  ),
                ),
                child: const Icon(
                  Icons.wb_twilight_rounded,
                  size: 36.0,
                  color: SanctuaryGlassTokens.brandSacredGold,
                ),
              ),
            ),
            const SizedBox(height: 20.0),

            // Header: Editorial Serif
            Text(
              "The Dawn Harvest",
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: SanctuaryTypography.serifFont,
                fontSize: 24.0,
                fontWeight: FontWeight.w700,
                color: tokens.textPrimary,
              ),
            ),
            const SizedBox(height: 8.0),

            // Subtitle
            Text(
              "Conscious rest brings intentional energy.",
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontSize: 14.0,
                color: tokens.textSecondary,
              ),
            ),
            const SizedBox(height: 20.0),

            // Sleep Duration Chip
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
              decoration: BoxDecoration(
                color: tokens.glassTintElevated,
                borderRadius: BorderRadius.circular(16.0),
                border: Border.all(color: tokens.borderSpecularStart.withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    Icons.bedtime_outlined,
                    size: 16.0,
                    color: SanctuaryGlassTokens.brandSacredGold,
                  ),
                  const SizedBox(width: 8.0),
                  Text(
                    "${widget.sleepHours.toStringAsFixed(1)} Hours Restful Slumber • ${multiplier}x Multiplier",
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.sansFont,
                      fontSize: 12.0,
                      fontWeight: FontWeight.w600,
                      color: tokens.textPrimary,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20.0),

            // Rewards Preview Row
            Wrap(
              spacing: 8.0,
              runSpacing: 8.0,
              alignment: WrapAlignment.center,
              children: [
                _buildRewardBadge(
                  icon: Icons.style_rounded,
                  label: "+$swipesAwarded Swipes",
                  color: SanctuaryGlassTokens.brandPine,
                ),
                _buildRewardBadge(
                  icon: Icons.offline_bolt_rounded,
                  label: "+$boostPointsAwarded Points",
                  color: SanctuaryGlassTokens.brandSacredGold,
                ),
                if (directLettersAwarded > 0)
                  _buildRewardBadge(
                    icon: Icons.mark_email_read_rounded,
                    label: "+$directLettersAwarded Direct Letters",
                    color: SanctuaryGlassTokens.brandTerracottaGlow,
                  ),
              ],
            ),
            const SizedBox(height: 24.0),

            if (_errorMessage != null) ...[
              Padding(
                padding: const EdgeInsets.only(bottom: 16.0),
                child: Text(
                  _errorMessage!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 12.0,
                    color: SanctuaryGlassTokens.alertRed,
                  ),
                ),
              ),
            ],

            // Action CTA Button
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: SanctuaryGlassTokens.brandSacredGold,
                foregroundColor: const Color(0xFF14171C),
                padding: const EdgeInsets.symmetric(vertical: 16.0),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(18.0),
                ),
                elevation: 0,
              ),
              onPressed: _isClaiming ? null : _claimHarvest,
              child: _isClaiming
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.0,
                        valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF14171C)),
                      ),
                    )
                  : const Text(
                      "Harvest Intentional Swipes",
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 15.0,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.2,
                      ),
                    ),
            ),
          ],
        ),
      ),
    ),
  );
}

  Widget _buildRewardBadge({
    required IconData icon,
    required String label,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(14.0),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14.0, color: color),
          const SizedBox(width: 6.0),
          Text(
            label,
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              fontSize: 12.0,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
