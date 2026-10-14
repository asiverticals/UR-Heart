import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../controllers/auth_controller.dart';
import '../widgets/underage_quarantine_dialog.dart';

/// Provider for GoogleSignIn instance, allowing test doubles to override authentication.
final googleSignInProvider = Provider<GoogleSignIn>((ref) {
  return GoogleSignIn(scopes: ['email', 'openid', 'profile']);
});

/// Strict 18+ Date-of-Birth gate paired with Google Sign-In and Magic Link entry.
/// Intercepts underage registration attempts and locks the device into quarantine.
class AgeGateAuthScreen extends ConsumerStatefulWidget {
  const AgeGateAuthScreen({super.key});

  @override
  ConsumerState<AgeGateAuthScreen> createState() => _AgeGateAuthScreenState();
}

class _AgeGateAuthScreenState extends ConsumerState<AgeGateAuthScreen> {
  final TextEditingController _emailController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _selectDateOfBirth(BuildContext context) async {
    final now = DateTime.now();
    final initialDate = DateTime(now.year - 20, now.month, now.day);
    final picked = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: DateTime(1920),
      lastDate: now,
      helpText: 'DECLARE YOUR DATE OF BIRTH',
      builder: (context, child) {
        final isDark = Theme.of(context).brightness == Brightness.dark;
        return Theme(
          data: isDark
              ? ThemeData.dark().copyWith(
                  colorScheme: const ColorScheme.dark(
                    primary: SanctuaryGlassTokens.brandSacredGold,
                    onPrimary: Colors.black,
                    surface: Color(0xFF181B20),
                    onSurface: Colors.white,
                  ),
                )
              : ThemeData.light().copyWith(
                  colorScheme: const ColorScheme.light(
                    primary: SanctuaryGlassTokens.brandTerracotta,
                    onPrimary: Colors.white,
                    surface: Color(0xFFF9F6F0),
                    onSurface: Colors.black,
                  ),
                ),
          child: child ?? const SizedBox(),
        );
      },
    );

    if (picked != null && mounted) {
      ref.read(authControllerProvider.notifier).updateDob(picked);
      await ref.read(authControllerProvider.notifier).verifyAgeAndRegisterIntent();
    }
  }

  @override
  Widget build(BuildContext context) {
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();
    final authState = ref.watch(authControllerProvider);

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: Stack(
        children: [
          // Background ambient gradient
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: isDark
                    ? [
                        const Color(0xFF0F1115),
                        const Color(0xFF161A22),
                        const Color(0xFF0F1115),
                      ]
                    : [
                        const Color(0xFFF9F6F0),
                        const Color(0xFFF3ECE2),
                        const Color(0xFFF9F6F0),
                      ],
              ),
            ),
            child: SafeArea(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Semantic Identifier
                      Semantics(
                        label: 'AgeGateAuthScreen',
                        child: Text(
                          'AgeGateAuthScreen',
                          style: TextStyle(
                            fontSize: 10,
                            color: tokens.textTertiary.withValues(alpha: 0.3),
                            fontFamily: SanctuaryTypography.sansFont,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),

                      // Central Frosted Card
                      SanctuaryGlassContainer(
                        blurSigma: 16.0,
                        borderRadius: 24.0,
                        padding: const EdgeInsets.all(24.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            // Header
                            Text(
                              'Declare Your Age',
                              style: SanctuaryTypography.titleH2(tokens.textPrimary, isDark: isDark),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Under statutory DPDP mandates, Sanctuary is exclusively reserved for seekers aged 18 and older.',
                              style: TextStyle(
                                fontFamily: SanctuaryTypography.sansFont,
                                fontSize: 13,
                                height: 1.4,
                                color: tokens.textSecondary,
                              ),
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 24),

                            // Date of Birth Selector Tile
                            SanctuaryGlassContainer(
                              blurSigma: 8.0,
                              borderRadius: 14.0,
                              onTap: authState.isLoading ? null : () => _selectDateOfBirth(context),
                              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                              customBorderGradient: authState.isEligible
                                  ? const LinearGradient(
                                      colors: [
                                        SanctuaryGlassTokens.onlineEmerald,
                                        Color(0x332EC4B6),
                                      ],
                                    )
                                  : null,
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.calendar_month_rounded,
                                    size: 20,
                                    color: authState.isEligible
                                        ? SanctuaryGlassTokens.onlineEmerald
                                        : SanctuaryGlassTokens.brandSacredGold,
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          'Date of Birth',
                                          style: TextStyle(
                                            fontFamily: SanctuaryTypography.sansFont,
                                            fontSize: 11,
                                            color: tokens.textTertiary,
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          authState.selectedDob != null
                                              ? '${authState.selectedDob!.day.toString().padLeft(2, '0')}/${authState.selectedDob!.month.toString().padLeft(2, '0')}/${authState.selectedDob!.year}'
                                              : 'Tap to select your birth date',
                                          style: TextStyle(
                                            fontFamily: SanctuaryTypography.sansFont,
                                            fontSize: 14,
                                            fontWeight: FontWeight.w600,
                                            color: tokens.textPrimary,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const Icon(
                                    Icons.arrow_drop_down_rounded,
                                    color: SanctuaryGlassTokens.brandSacredGold,
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 12),

                            // Age Verification Badge based strictly on server verdict
                            if (authState.isUnderageQuarantined)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(10),
                                  color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.12),
                                  border: Border.all(
                                    color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.35),
                                  ),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    const Icon(
                                      Icons.warning_amber_rounded,
                                      size: 16,
                                      color: SanctuaryGlassTokens.alertRed,
                                    ),
                                    const SizedBox(width: 8),
                                    Text(
                                      'Underage (Age: ${authState.calculatedAge ?? ""}). Quarantined.',
                                      style: const TextStyle(
                                        fontFamily: SanctuaryTypography.sansFont,
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                        color: SanctuaryGlassTokens.alertRed,
                                      ),
                                    ),
                                  ],
                                ),
                              )
                            else if (authState.isServerApproved)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(10),
                                  color: SanctuaryGlassTokens.onlineEmerald.withValues(alpha: 0.12),
                                  border: Border.all(
                                    color: SanctuaryGlassTokens.onlineEmerald.withValues(alpha: 0.35),
                                  ),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    const Icon(
                                      Icons.verified_rounded,
                                      size: 16,
                                      color: SanctuaryGlassTokens.onlineEmerald,
                                    ),
                                    const SizedBox(width: 8),
                                    Text(
                                      'Verified 18+ (Age: ${authState.calculatedAge})',
                                      style: const TextStyle(
                                        fontFamily: SanctuaryTypography.sansFont,
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                        color: SanctuaryGlassTokens.onlineEmerald,
                                      ),
                                    ),
                                  ],
                                ),
                              ),

                            // Error Message Banner
                            if (authState.errorMessage != null && !authState.isUnderageQuarantined) ...[
                              const SizedBox(height: 12),
                              Text(
                                authState.errorMessage!,
                                style: const TextStyle(
                                  fontFamily: SanctuaryTypography.sansFont,
                                  fontSize: 12,
                                  color: SanctuaryGlassTokens.alertRed,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],

                            // Unlocked Authentication Handshake
                            if (authState.isServerApproved) ...[
                              const SizedBox(height: 28),
                              const Divider(height: 1),
                              const SizedBox(height: 20),

                              // Google One-Tap Action
                              SanctuaryGlassContainer(
                                blurSigma: 12.0,
                                borderRadius: 14.0,
                                height: 50,
                                customTint: isDark
                                    ? const Color(0x22FFFFFF)
                                    : const Color(0xCCFFFFFF),
                                onTap: authState.isLoading
                                    ? null
                                    : () async {
                                        try {
                                          final googleSignIn = ref.read(googleSignInProvider);
                                          final account = await googleSignIn.signIn();
                                          if (account == null) return;
                                          final auth = await account.authentication;
                                          final idToken = auth.idToken;
                                          if (idToken != null && idToken.isNotEmpty) {
                                            final success = await ref
                                                .read(authControllerProvider.notifier)
                                                .syncGoogleUser(idToken);
                                            if (success && context.mounted) {
                                              context.go('/main');
                                            }
                                          } else {
                                            if (context.mounted) {
                                              ScaffoldMessenger.of(context).showSnackBar(
                                                const SnackBar(
                                                  content: Text('Failed to obtain authentication token from Google.'),
                                                ),
                                              );
                                            }
                                          }
                                        } catch (e) {
                                          if (context.mounted) {
                                            ScaffoldMessenger.of(context).showSnackBar(
                                              SnackBar(
                                                content: Text('Google Sign-In failed: $e'),
                                              ),
                                            );
                                          }
                                        }
                                      },
                                child: Center(
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      const Icon(
                                        Icons.g_mobiledata_rounded,
                                        size: 26,
                                        color: SanctuaryGlassTokens.brandSacredGold,
                                      ),
                                      const SizedBox(width: 6),
                                      Text(
                                        'Continue with Google',
                                        style: TextStyle(
                                          fontFamily: SanctuaryTypography.sansFont,
                                          fontSize: 14,
                                          fontWeight: FontWeight.w600,
                                          color: tokens.textPrimary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(height: 18),

                              // Or divider
                              Row(
                                children: [
                                  Expanded(child: Divider(color: tokens.textTertiary.withValues(alpha: 0.3))),
                                  Padding(
                                    padding: const EdgeInsets.symmetric(horizontal: 12.0),
                                    child: Text(
                                      'or passwordless email',
                                      style: TextStyle(
                                        fontFamily: SanctuaryTypography.sansFont,
                                        fontSize: 11,
                                        color: tokens.textTertiary,
                                      ),
                                    ),
                                  ),
                                  Expanded(child: Divider(color: tokens.textTertiary.withValues(alpha: 0.3))),
                                ],
                              ),
                              const SizedBox(height: 18),

                              // Magic Link Input
                              TextField(
                                controller: _emailController,
                                keyboardType: TextInputType.emailAddress,
                                style: TextStyle(
                                  fontFamily: SanctuaryTypography.sansFont,
                                  fontSize: 14,
                                  color: tokens.textPrimary,
                                ),
                                decoration: InputDecoration(
                                  hintText: 'seeker@sanctuary.in',
                                  hintStyle: TextStyle(
                                    color: tokens.textTertiary,
                                    fontSize: 13,
                                  ),
                                  prefixIcon: Icon(
                                    Icons.mail_outline_rounded,
                                    size: 18,
                                    color: tokens.textTertiary,
                                  ),
                                  filled: true,
                                  fillColor: isDark
                                      ? const Color(0x15FFFFFF)
                                      : const Color(0x77FFFFFF),
                                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                                  border: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(12),
                                    borderSide: BorderSide(
                                      color: tokens.borderSpecularStart.withValues(alpha: 0.5),
                                    ),
                                  ),
                                  enabledBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(12),
                                    borderSide: BorderSide(
                                      color: tokens.borderSpecularStart.withValues(alpha: 0.3),
                                    ),
                                  ),
                                  focusedBorder: OutlineInputBorder(
                                    borderRadius: BorderRadius.circular(12),
                                    borderSide: const BorderSide(
                                      color: SanctuaryGlassTokens.brandSacredGold,
                                      width: 1.5,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 14),

                              // Dispatch Magic Link Button
                              SanctuaryGlassContainer(
                                blurSigma: 12.0,
                                borderRadius: 14.0,
                                height: 48,
                                customBorderGradient: const LinearGradient(
                                  colors: [
                                    SanctuaryGlassTokens.brandSacredGold,
                                    SanctuaryGlassTokens.brandTerracotta,
                                  ],
                                ),
                                customTint: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
                                onTap: authState.isLoading
                                    ? null
                                    : () {
                                        ref
                                            .read(authControllerProvider.notifier)
                                            .sendMagicLink(_emailController.text);
                                      },
                                child: Center(
                                  child: authState.isLoading
                                      ? const SizedBox(
                                          width: 20,
                                          height: 20,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                            color: SanctuaryGlassTokens.brandSacredGold,
                                          ),
                                        )
                                      : const Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(
                                              Icons.send_rounded,
                                              size: 16,
                                              color: SanctuaryGlassTokens.brandSacredGold,
                                            ),
                                            SizedBox(width: 8),
                                            Text(
                                              'Send Sacred Link',
                                              style: TextStyle(
                                                fontFamily: SanctuaryTypography.sansFont,
                                                fontSize: 14,
                                                fontWeight: FontWeight.w600,
                                                color: SanctuaryGlassTokens.brandSacredGold,
                                              ),
                                            ),
                                          ],
                                        ),
                                ),
                              ),

                              // Magic Link Dispatched Confirmation
                              if (authState.magicLinkSentEmail != null) ...[
                                const SizedBox(height: 14),
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(10),
                                    color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.1),
                                    border: Border.all(
                                      color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.3),
                                    ),
                                  ),
                                  child: Row(
                                    children: [
                                      const Icon(
                                        Icons.mark_email_read_rounded,
                                        size: 18,
                                        color: SanctuaryGlassTokens.brandSacredGold,
                                      ),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Text(
                                          'Sacred link dispatched to ${authState.magicLinkSentEmail}. Open link on this device to enter.',
                                          style: TextStyle(
                                            fontFamily: SanctuaryTypography.sansFont,
                                            fontSize: 12,
                                            color: tokens.textPrimary,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Underage Quarantine Lockout Barrier
          if (authState.isUnderageQuarantined)
            Container(
              color: Colors.black.withValues(alpha: 0.85),
              child: UnderageQuarantineDialog(
                quarantineUntil: authState.quarantineUntil,
              ),
            ),
        ],
      ),
    );
  }
}
