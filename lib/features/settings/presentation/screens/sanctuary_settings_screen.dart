import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../../../legal_vault/presentation/widgets/account_incineration_dialog.dart';

/// Settings screen hosting sanctuary preferences and statutory data privacy controls.
class SanctuarySettingsScreen extends StatelessWidget {
  const SanctuarySettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          'Sanctuary Settings',
          style: TextStyle(
            fontFamily: SanctuaryTypography.serifFont,
            fontSize: 20.0,
            fontWeight: FontWeight.w700,
            color: tokens.textPrimary,
          ),
        ),
        centerTitle: true,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 16.0),
          children: [
            // Section Header: Privacy & Statutory Data Rights
            Padding(
              padding: const EdgeInsets.only(left: 4.0, bottom: 8.0),
              child: Text(
                'PRIVACY & STATUTORY DATA RIGHTS',
                style: TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.2,
                  color: tokens.textTertiary,
                ),
              ),
            ),

            // Incinerate Sacred Persona Glass Tile
            SanctuaryGlassContainer(
              blurSigma: 16.0,
              borderRadius: 18.0,
              borderWidth: 1.0,
              customBorderGradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  SanctuaryGlassTokens.alertRed.withValues(alpha: 0.35),
                  SanctuaryGlassTokens.alertRed.withValues(alpha: 0.1),
                ],
              ),
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 14.0),
              child: InkWell(
                key: const Key('incinerate_persona_tile'),
                borderRadius: BorderRadius.circular(16.0),
                onTap: () async {
                  final incinerated = await AccountIncinerationDialog.show(context);
                  if (incinerated == true && context.mounted) {
                    context.go('/consent');
                  }
                },
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.15),
                      ),
                      child: const Icon(
                        Icons.delete_forever_outlined,
                        color: SanctuaryGlassTokens.alertRed,
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Incinerate Sacred Persona',
                            style: TextStyle(
                              fontFamily: SanctuaryTypography.serifFont,
                              fontSize: 16.0,
                              fontWeight: FontWeight.w700,
                              color: tokens.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            'Permanently wipe account and media under DPDP Act 2023',
                            style: TextStyle(
                              fontFamily: SanctuaryTypography.sansFont,
                              fontSize: 12.0,
                              color: tokens.textSecondary,
                              height: 1.3,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Icon(
                      Icons.chevron_right_rounded,
                      color: tokens.textTertiary,
                      size: 20,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
