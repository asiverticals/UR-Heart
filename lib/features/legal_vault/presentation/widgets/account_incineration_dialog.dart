import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/constants/app_typography.dart';
import '../../../../core/network/sanctuary_http_client.dart';
import '../../../../core/services/window_security_service.dart';
import '../../../../core/storage/secure_session_storage.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

/// Modal dialog enforcing statutory 5-second mindfulness lockout and cryptographic confirmation phrase
/// before permanently expunging seeker persona and media under DPDP Act 2023 Section 12.
class AccountIncinerationDialog extends ConsumerStatefulWidget {
  const AccountIncinerationDialog({super.key});

  static Future<bool?> show(BuildContext context) {
    return showDialog<bool>(
      context: context,
      barrierDismissible: false,
      barrierColor: Colors.black.withValues(alpha: 0.75),
      builder: (ctx) => const AccountIncinerationDialog(),
    );
  }

  @override
  ConsumerState<AccountIncinerationDialog> createState() => _AccountIncinerationDialogState();
}

class _AccountIncinerationDialogState extends ConsumerState<AccountIncinerationDialog> {
  static const String requiredPhrase = 'PERMANENTLY INCINERATE';
  static const int initialLockoutSeconds = 5;

  late final TextEditingController _phraseController;
  Timer? _countdownTimer;
  int _secondsRemaining = initialLockoutSeconds;
  bool _isIncinerating = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _phraseController = TextEditingController();
    _phraseController.addListener(_onPhraseChanged);
    _startCountdown();
  }

  void _onPhraseChanged() {
    setState(() {});
  }

  void _startCountdown() {
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        if (_secondsRemaining > 1) {
          _secondsRemaining--;
        } else {
          _secondsRemaining = 0;
          timer.cancel();
        }
      });
    });
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    _phraseController.removeListener(_onPhraseChanged);
    _phraseController.dispose();
    super.dispose();
  }

  bool get _canIncinerate {
    return _secondsRemaining == 0 &&
        _phraseController.text.trim() == requiredPhrase &&
        !_isIncinerating;
  }

  Future<void> _executeIncineration() async {
    if (!_canIncinerate) return;

    _countdownTimer?.cancel();

    setState(() {
      _isIncinerating = true;
      _errorMessage = null;
    });

    try {
      final client = ref.read(sanctuaryHttpClientProvider);
      await client.delete(
        '/api/v1/legal/account',
        body: {'confirmation_phrase': requiredPhrase},
      );

      final storage = ref.read(secureSessionStorageProvider);
      await storage.clearSession();
      await WindowSecurityService.relaxWindowProtection();

      if (mounted) {
        Navigator.of(context, rootNavigator: true).pop(true);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isIncinerating = false;
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return PopScope(
      canPop: !_isIncinerating,
      child: Center(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 24.0),
            child: SanctuaryGlassContainer(
            blurSigma: 24.0, // Tier 3 Modal Glass
            borderRadius: 24.0,
            borderWidth: 1.5,
            customBorderGradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                SanctuaryGlassTokens.alertRed,
                SanctuaryGlassTokens.alertRed.withValues(alpha: 0.25),
              ],
            ),
            padding: const EdgeInsets.all(24.0),
            child: Material(
              color: Colors.transparent,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Top Alert Red Fire Icon with soft ambient aura
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
                      boxShadow: [
                        BoxShadow(
                          color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.25),
                          blurRadius: 16.0,
                          spreadRadius: 2.0,
                        ),
                      ],
                    ),
                    child: const Icon(
                      Icons.local_fire_department_outlined,
                      color: SanctuaryGlassTokens.alertRed,
                      size: 32,
                    ),
                  ),
                  const SizedBox(height: 18),

                  // Header
                  Text(
                    'Incinerate Sacred Persona',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.serifFont,
                      fontSize: 22.0,
                      fontWeight: FontWeight.w700,
                      color: tokens.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 10),

                  // Statutory Subtitle
                  Text(
                    'Section 12 DPDP Act 2023 Erasure. This action is irreversible. '
                    'All photos, voice sparks, matches, and dialogues will be permanently expunged.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.sansFont,
                      fontSize: 13.0,
                      height: 1.45,
                      color: tokens.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Mandatory Confirmation Phrase Textfield
                  Container(
                    decoration: BoxDecoration(
                      color: isDark ? const Color(0x1AFFFFFF) : const Color(0x0D000000),
                      borderRadius: BorderRadius.circular(14.0),
                      border: Border.all(
                        color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.35),
                        width: 1.0,
                      ),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 4.0),
                    child: TextField(
                      key: const Key('incineration_phrase_field'),
                      controller: _phraseController,
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 14.0,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                        color: tokens.textPrimary,
                      ),
                      decoration: InputDecoration(
                        border: InputBorder.none,
                        hintText: 'Type "PERMANENTLY INCINERATE"',
                        hintStyle: TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          fontSize: 13.0,
                          color: tokens.textTertiary,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Countdown notice or error
                  if (_errorMessage != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10.0),
                      child: Text(
                        _errorMessage!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: SanctuaryGlassTokens.alertRed,
                          fontSize: 12.0,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    )
                  else if (_secondsRemaining > 0)
                    Text(
                      'Mindfulness lockout active: ${_secondsRemaining}s',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 12.0,
                        fontWeight: FontWeight.w600,
                        color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.85),
                      ),
                    )
                  else
                    Text(
                      'Exact phrase match required to unseal incinerator',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 12.0,
                        color: tokens.textTertiary,
                      ),
                    ),
                  const SizedBox(height: 20),

                  // CTA Confirmation Button
                  SizedBox(
                    width: double.infinity,
                    height: 48,
                    child: ElevatedButton(
                      key: const Key('confirm_incineration_button'),
                      onPressed: _canIncinerate ? _executeIncineration : null,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: SanctuaryGlassTokens.alertRed,
                        disabledBackgroundColor:
                            SanctuaryGlassTokens.alertRed.withValues(alpha: 0.3),
                        foregroundColor: Colors.white,
                        disabledForegroundColor: Colors.white54,
                        elevation: _canIncinerate ? 6.0 : 0.0,
                        shadowColor: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.45),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14.0),
                        ),
                      ),
                      child: _isIncinerating
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.0,
                                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                              ),
                            )
                          : Text(
                              _secondsRemaining > 0
                                  ? 'Mindfulness Hold (${_secondsRemaining}s)'
                                  : 'Confirm Permanent Incineration',
                              style: const TextStyle(
                                fontFamily: SanctuaryTypography.sansFont,
                                fontSize: 14.0,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 0.3,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(height: 10),

                  // Cancel / Keep Persona Button
                  TextButton(
                    onPressed: _isIncinerating ? null : () => Navigator.of(context).pop(false),
                    child: Text(
                      'Preserve Sacred Persona',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 13.0,
                        fontWeight: FontWeight.w600,
                        color: tokens.textSecondary,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
}
