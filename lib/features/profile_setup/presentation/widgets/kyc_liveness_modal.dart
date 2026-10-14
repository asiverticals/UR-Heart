import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../controllers/profile_setup_controller.dart';

enum KycLivenessStep {
  ready,
  countdown,
  analyzing,
  approved,
  escalated,
  rejected,
}

/// Tier 3 Modal Glass overlay for DPDP statutory biometric facial liveness check.
/// Verifies conscious presence via Groq Vision API with <60s ephemeral purge guarantee.
class KycLivenessModal extends ConsumerStatefulWidget {
  final Future<List<int>?> Function()? onCaptureLiveFrame;

  const KycLivenessModal({
    super.key,
    this.onCaptureLiveFrame,
  });

  static Future<bool?> show(
    BuildContext context, {
    Future<List<int>?> Function()? onCaptureLiveFrame,
  }) {
    return showDialog<bool>(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black.withValues(alpha: 0.65),
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: KycLivenessModal(onCaptureLiveFrame: onCaptureLiveFrame),
      ),
    );
  }

  @override
  ConsumerState<KycLivenessModal> createState() => _KycLivenessModalState();
}

class _KycLivenessModalState extends ConsumerState<KycLivenessModal>
    with SingleTickerProviderStateMixin {
  KycLivenessStep _step = KycLivenessStep.ready;
  int _countdown = 3;
  Timer? _countdownTimer;
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;
  String? _statusDetail;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 0.95, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    _pulseController.dispose();
    super.dispose();
  }

  void _startCountdown() {
    setState(() {
      _step = KycLivenessStep.countdown;
      _countdown = 3;
    });

    _countdownTimer?.cancel();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (_countdown > 1) {
        setState(() => _countdown--);
      } else {
        timer.cancel();
        _performCaptureAndVerify();
      }
    });
  }

  Future<void> _performCaptureAndVerify() async {
    setState(() => _step = KycLivenessStep.analyzing);

    List<int>? bytes;
    if (widget.onCaptureLiveFrame != null) {
      bytes = await widget.onCaptureLiveFrame!();
    }

    if (bytes == null || bytes.isEmpty) {
      if (mounted) {
        setState(() {
          _step = KycLivenessStep.rejected;
          _statusDetail = 'Unable to capture live selfie frame.';
        });
      }
      return;
    }

    final success = await ref
        .read(profileSetupControllerProvider.notifier)
        .submitKycLiveness(bytes);

    if (!mounted) return;

    final controllerState = ref.read(profileSetupControllerProvider);
    final status = controllerState.kycStatus;
    final msg = controllerState.kycStatusMessage;

    if (success || status == 'approved') {
      setState(() {
        _step = KycLivenessStep.approved;
        _statusDetail = msg ?? 'Identity Confirmed';
      });
      Future.delayed(const Duration(milliseconds: 1500), () {
        if (mounted && Navigator.of(context).canPop()) {
          Navigator.of(context).pop(true);
        }
      });
    } else if (status == 'escalated') {
      setState(() {
        _step = KycLivenessStep.escalated;
        _statusDetail = msg ?? 'Manual sanctuary review pending.';
      });
    } else {
      setState(() {
        _step = KycLivenessStep.rejected;
        _statusDetail = msg ?? 'Facial resonance mismatch.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return SanctuaryGlassContainer(
      width: double.infinity,
      borderRadius: 24,
      blurSigma: 24.0,
      padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 26),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Close button
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              IconButton(
                onPressed: _step == KycLivenessStep.analyzing
                    ? null
                    : () => Navigator.of(context).pop(false),
                icon: Icon(Icons.close_rounded, color: tokens.textSecondary, size: 22),
              ),
            ],
          ),

          // Headline
          Text(
            'Sacred Liveness Verification',
            style: TextStyle(
              fontFamily: SanctuaryTypography.serifFont,
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: tokens.textPrimary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),

          // Subtitle & DPDP Statutory Notice
          Text(
            'A quick 3-second gentle blink confirms your conscious presence. '
            'Biometric data is permanently incinerated in <60s under DPDP Act.',
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              fontSize: 12,
              height: 1.4,
              color: tokens.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),

          // Viewfinder circular frame
          _buildViewfinder(tokens),
          const SizedBox(height: 24),

          // Dynamic state actions
          _buildActionSection(tokens),
        ],
      ),
    );
  }

  Widget _buildViewfinder(SanctuaryGlassTokens tokens) {
    return Center(
      child: AnimatedBuilder(
        animation: _pulseAnimation,
        builder: (context, child) {
          final scale = _step == KycLivenessStep.countdown ? _pulseAnimation.value : 1.0;
          return Transform.scale(
            scale: scale,
            child: Container(
              width: 170,
              height: 170,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: _getViewfinderBorderColor(),
                  width: 3.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: _getViewfinderBorderColor().withValues(alpha: 0.25),
                    blurRadius: 18,
                    spreadRadius: 2,
                  ),
                ],
                color: Colors.black.withValues(alpha: 0.25),
              ),
              child: Center(
                child: _buildViewfinderContent(tokens),
              ),
            ),
          );
        },
      ),
    );
  }

  Color _getViewfinderBorderColor() {
    switch (_step) {
      case KycLivenessStep.ready:
      case KycLivenessStep.countdown:
      case KycLivenessStep.analyzing:
        return SanctuaryGlassTokens.brandSacredGold;
      case KycLivenessStep.approved:
        return SanctuaryGlassTokens.onlineEmerald;
      case KycLivenessStep.escalated:
        return SanctuaryGlassTokens.brandTerracottaGlow;
      case KycLivenessStep.rejected:
        return SanctuaryGlassTokens.alertRed;
    }
  }

  Widget _buildViewfinderContent(SanctuaryGlassTokens tokens) {
    switch (_step) {
      case KycLivenessStep.ready:
        return Icon(
          Icons.face_retouching_natural_rounded,
          size: 64,
          color: tokens.textTertiary,
        );
      case KycLivenessStep.countdown:
        return Text(
          '$_countdown',
          style: const TextStyle(
            fontFamily: SanctuaryTypography.serifFont,
            fontSize: 54,
            fontWeight: FontWeight.w700,
            color: SanctuaryGlassTokens.brandSacredGold,
          ),
        );
      case KycLivenessStep.analyzing:
        return const SizedBox(
          width: 50,
          height: 50,
          child: CircularProgressIndicator(
            strokeWidth: 3.0,
            valueColor: AlwaysStoppedAnimation(SanctuaryGlassTokens.brandSacredGold),
          ),
        );
      case KycLivenessStep.approved:
        return const Icon(
          Icons.check_circle_rounded,
          size: 72,
          color: SanctuaryGlassTokens.onlineEmerald,
        );
      case KycLivenessStep.escalated:
        return const Icon(
          Icons.hourglass_top_rounded,
          size: 64,
          color: SanctuaryGlassTokens.brandTerracottaGlow,
        );
      case KycLivenessStep.rejected:
        return const Icon(
          Icons.highlight_off_rounded,
          size: 72,
          color: SanctuaryGlassTokens.alertRed,
        );
    }
  }

  Widget _buildActionSection(SanctuaryGlassTokens tokens) {
    switch (_step) {
      case KycLivenessStep.ready:
        return ElevatedButton.icon(
          style: ElevatedButton.styleFrom(
            backgroundColor: SanctuaryGlassTokens.brandSacredGold,
            foregroundColor: Colors.black,
            minimumSize: const Size(double.infinity, 50),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
          onPressed: _startCountdown,
          icon: const Icon(Icons.videocam_outlined, size: 20),
          label: const Text(
            'Begin 3s Check',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
          ),
        );

      case KycLivenessStep.countdown:
        return Text(
          'Blink naturally into frame...',
          style: TextStyle(
            fontFamily: SanctuaryTypography.sansFont,
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: tokens.textSecondary,
          ),
        );

      case KycLivenessStep.analyzing:
        return Text(
          'Groq Vision AI evaluating liveness...',
          style: TextStyle(
            fontFamily: SanctuaryTypography.sansFont,
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: tokens.textPrimary,
          ),
        );

      case KycLivenessStep.approved:
        return Column(
          children: [
            const Text(
              'Identity Confirmed',
              style: TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: SanctuaryGlassTokens.onlineEmerald,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Biometrics incinerated under DPDP Sec 8.',
              style: TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontSize: 11,
                color: tokens.textSecondary,
              ),
            ),
          ],
        );

      case KycLivenessStep.escalated:
        return Column(
          children: [
            const Text(
              'Dossier Under Sanctuary Review',
              style: TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: SanctuaryGlassTokens.brandTerracottaGlow,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              _statusDetail ?? 'Manual sanctuary review pending.',
              style: TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontSize: 12,
                color: tokens.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 14),
            OutlinedButton(
              onPressed: () => Navigator.of(context).pop(false),
              style: OutlinedButton.styleFrom(
                foregroundColor: tokens.textPrimary,
                side: BorderSide(color: tokens.textTertiary),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Continue to Deck'),
            ),
          ],
        );

      case KycLivenessStep.rejected:
        return Column(
          children: [
            Text(
              _statusDetail ?? 'Facial resonance mismatch.',
              style: const TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: SanctuaryGlassTokens.alertRed,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: SanctuaryGlassTokens.alertRed,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: _startCountdown,
              child: const Text('Retry Check'),
            ),
          ],
        );
    }
  }
}
