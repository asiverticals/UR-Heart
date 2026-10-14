import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

/// First launch screen presenting DPDP Act 2023 purpose limitations,
/// anti-screenshot FLAG_SECURE notification, and mindful 10-swipe daily limits.
class ConsentScreen extends ConsumerStatefulWidget {
  const ConsentScreen({super.key});

  static const String consentRecordKey = 'dpdp_statutory_consent_record_v1';

  @override
  ConsumerState<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends ConsumerState<ConsentScreen> {

  bool _consentPurposeLimitation = false;
  bool _consentAntiCapture = false;
  bool _consentRhythmAllowance = false;

  bool get _allConsentsAffirmed =>
      _consentPurposeLimitation && _consentAntiCapture && _consentRhythmAllowance;

  Future<void> _handleConsentAffirmation(BuildContext context) async {
    final purpose = _consentPurposeLimitation;
    final antiCapture = _consentAntiCapture;
    final rhythm = _consentRhythmAllowance;

    if (!purpose || !antiCapture || !rhythm) return;

    try {
      final prefs = await SharedPreferences.getInstance();
      final record = jsonEncode({
        'version': '1.0',
        'timestamp': DateTime.now().toUtc().toIso8601String(),
        'purpose_limitation': purpose,
        'flag_secure_anti_capture': antiCapture,
        'rhythm_10_swipe': rhythm,
      });
      final saved = await prefs.setString(ConsentScreen.consentRecordKey, record);
      if (!saved) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Failed to persist statutory consent. Please try again.'),
            ),
          );
        }
        return;
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error saving consent: $e'),
          ),
        );
      }
      return;
    }

    if (context.mounted) {
      context.go('/auth');
    }
  }

  void _toggleAll(bool value) {
    setState(() {
      _consentPurposeLimitation = value;
      _consentAntiCapture = value;
      _consentRhythmAllowance = value;
    });
  }

  @override
  Widget build(BuildContext context) {
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isDark
                ? [
                    const Color(0xFF0F1115),
                    const Color(0xFF141923),
                    const Color(0xFF0F1115),
                  ]
                : [
                    const Color(0xFFF9F6F0),
                    const Color(0xFFF0EAE1),
                    const Color(0xFFF9F6F0),
                  ],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Top Bar: Semantic identifier + Theme Toggle Pill
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 8.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Semantics(
                      label: 'ConsentScreen',
                      child: Text(
                        'ConsentScreen',
                        style: TextStyle(
                          fontSize: 10,
                          color: tokens.textTertiary.withValues(alpha: 0.5),
                          fontFamily: SanctuaryTypography.sansFont,
                        ),
                      ),
                    ),
                    // Theme Toggle Pill
                    SanctuaryGlassContainer(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      borderRadius: 20,
                      blurSigma: 8.0,
                      onTap: () => ref.read(themeProvider.notifier).toggleTheme(),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            isDark ? Icons.dark_mode_rounded : Icons.light_mode_rounded,
                            size: 16,
                            color: SanctuaryGlassTokens.brandSacredGold,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            isDark ? 'Dark Sanctuary' : 'Light Sanctuary',
                            style: TextStyle(
                              fontFamily: SanctuaryTypography.sansFont,
                              fontSize: 11,
                              fontWeight: FontWeight.w500,
                              color: tokens.textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              // Editorial Header
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 16),
                child: Column(
                  children: [
                    Text(
                      'Welcome to UR-Heart Sanctuary',
                      style: SanctuaryTypography.titleH1(tokens.textPrimary, isDark: isDark),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'A sacred, intentional space honoring digital privacy, conscious connection, and psychological sovereignty.',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 13,
                        height: 1.4,
                        color: tokens.textSecondary,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),

              // Quick "Affirm All" Toggle
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 4.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    GestureDetector(
                      onTap: () => _toggleAll(!_allConsentsAffirmed),
                      child: Text(
                        _allConsentsAffirmed ? 'Deselect All' : 'Affirm All Clauses',
                        style: const TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: SanctuaryGlassTokens.brandSacredGold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // 3 Scrollable Frosted Consent Cards
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 8.0),
                  children: [
                    _buildConsentCard(
                      tokens: tokens,
                      isDark: isDark,
                      icon: Icons.verified_user_outlined,
                      iconColor: SanctuaryGlassTokens.brandSacredGold,
                      title: 'DPDP Section 6 Purpose Limitation',
                      subtitle:
                          'Under India DPDP Act 2023, personal data is processed solely for sacred matchmaking. Zero third-party data brokerage, zero behavioral ad tracking, and hardware Keystore AES-256 GCM encryption.',
                      value: _consentPurposeLimitation,
                      onChanged: (v) => setState(() => _consentPurposeLimitation = v ?? false),
                    ),
                    const SizedBox(height: 14),
                    _buildConsentCard(
                      tokens: tokens,
                      isDark: isDark,
                      icon: Icons.no_photography_outlined,
                      iconColor: SanctuaryGlassTokens.brandTerracotta,
                      title: 'FLAG_SECURE Anti-Capture Shield',
                      subtitle:
                          'Sanctuary activates OS-level display protection. Screenshots, screen recordings, and external screen cloning are intercepted and blocked at the hardware display pipeline.',
                      value: _consentAntiCapture,
                      onChanged: (v) => setState(() => _consentAntiCapture = v ?? false),
                    ),
                    const SizedBox(height: 14),
                    _buildConsentCard(
                      tokens: tokens,
                      isDark: isDark,
                      icon: Icons.hourglass_empty_rounded,
                      iconColor: SanctuaryGlassTokens.brandPine,
                      title: '10-Swipe Daily Mindful Rhythm',
                      subtitle:
                          'To protect emotional well-being and eradicate doomscrolling, discovery is limited to 10 conscious profiles daily. Matches require mutual intentionality before dialogue begins.',
                      value: _consentRhythmAllowance,
                      onChanged: (v) => setState(() => _consentRhythmAllowance = v ?? false),
                    ),
                    const SizedBox(height: 20),
                  ],
                ),
              ),

              // Affirm & Enter CTA Button
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 20),
                child: Opacity(
                  opacity: _allConsentsAffirmed ? 1.0 : 0.45,
                  child: SanctuaryGlassContainer(
                    width: double.infinity,
                    height: 56,
                    borderRadius: 16,
                    blurSigma: 16.0,
                    customBorderGradient: _allConsentsAffirmed
                        ? const LinearGradient(
                            colors: [
                              SanctuaryGlassTokens.brandSacredGold,
                              SanctuaryGlassTokens.brandTerracottaGlow,
                            ],
                          )
                        : null,
                    customTint: _allConsentsAffirmed
                        ? SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15)
                        : null,
                    onTap: _allConsentsAffirmed ? () => _handleConsentAffirmation(context) : null,
                    child: Center(
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.check_circle_outline_rounded,
                            size: 18,
                            color: _allConsentsAffirmed
                                ? SanctuaryGlassTokens.brandSacredGold
                                : tokens.textTertiary,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'I Affirm & Enter the Sanctuary',
                            style: TextStyle(
                              fontFamily: SanctuaryTypography.sansFont,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.2,
                              color: _allConsentsAffirmed
                                 ? tokens.textPrimary
                                  : tokens.textTertiary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildConsentCard({
    required SanctuaryGlassTokens tokens,
    required bool isDark,
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool?> onChanged,
  }) {
    return SanctuaryGlassContainer(
      blurSigma: 12.0,
      borderRadius: 16.0,
      padding: const EdgeInsets.all(16.0),
      customBorderGradient: value
          ? LinearGradient(
              colors: [
                iconColor.withValues(alpha: 0.8),
                iconColor.withValues(alpha: 0.2),
              ],
            )
          : null,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Checkbox(
            value: value,
            activeColor: iconColor,
            checkColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
            onChanged: onChanged,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(icon, size: 18, color: iconColor),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        title,
                        style: TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: tokens.textPrimary,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 12,
                    height: 1.4,
                    color: tokens.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
