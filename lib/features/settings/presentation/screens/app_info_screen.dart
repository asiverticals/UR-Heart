import 'package:flutter/material.dart';
import 'package:ur_heart/core/constants/app_typography.dart';
import 'package:ur_heart/core/theme/glass_tokens.dart';
import 'package:ur_heart/core/theme/widgets/sanctuary_glass_container.dart';

/// Screen displaying App Information, Versioning, DPDP Act 2023 disclosures,
/// Resident Grievance Officer charter (IT Rules 2021 Rule 3(2)(a)), and
/// links to statutory Terms of Service, Privacy Policy, and Open Source Licenses.
class AppInfoScreen extends StatelessWidget {
  const AppInfoScreen({super.key});

  static const String appName = 'UR-Heart Sanctuary';
  static const String packageName = 'ur_heart';
  static const String appVersion = '1.0.0+1';
  static const String buildLabel = 'Build 2026.10';

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      appBar: AppBar(
        title: Text(
          'App Info & Legal Sanctuary',
          style: TextStyle(
            fontFamily: SanctuaryTypography.serifFont,
            fontSize: 20.0,
            fontWeight: FontWeight.w700,
            color: tokens.textPrimary,
          ),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: IconThemeData(color: tokens.textPrimary),
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 16.0),
          children: [
            // Hero Brand Header
            Center(
              child: Column(
                children: [
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: [tokens.glowTerracotta, tokens.glowGold],
                      ),
                    ),
                    child: const Icon(Icons.favorite_rounded, color: Colors.white, size: 38),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    appName,
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.serifFont,
                      fontSize: 26.0,
                      fontWeight: FontWeight.w700,
                      color: tokens.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Version $appVersion ($buildLabel)',
                    style: SanctuaryTypography.bodyStandard(tokens.textSecondary),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Mindful Connection Sanctuary for Resonant Souls',
                    style: SanctuaryTypography.caption(tokens.textTertiary),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Operating Organization & Fiduciary Details
            SanctuaryGlassContainer(
              borderRadius: 16.0,
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionHeader(
                    icon: Icons.business_outlined,
                    title: 'Operating Data Fiduciary',
                    subtitle: 'Digital Personal Data Protection Act 2023',
                    tokens: tokens,
                  ),
                  const SizedBox(height: 12),
                  _buildInfoRow('Legal Entity', 'ASI Verticals Private Limited', tokens),
                  _buildInfoRow('Jurisdiction', 'Republic of India (New Delhi)', tokens),
                  _buildInfoRow(
                    'Sanctuary Operations Desk',
                    'Level 4, Tower B, Sector 62, Noida, Gautam Buddha Nagar, Uttar Pradesh 201309, India',
                    tokens,
                  ),
                  _buildInfoRow('Official Portal', 'https://urheart.app', tokens),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Resident Grievance Officer Charter (IT Rules 2021 Rule 3(2)(a))
            SanctuaryGlassContainer(
              borderRadius: 16.0,
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionHeader(
                    icon: Icons.gavel_outlined,
                    title: 'Designated Resident Grievance Officer',
                    subtitle: 'Rule 3(2)(a) IT Rules 2021 & DPDP Act §13',
                    tokens: tokens,
                  ),
                  const SizedBox(height: 12),
                  _buildInfoRow('Officer Name', 'Adv. Vikramaditya Sen', tokens),
                  _buildInfoRow('Designation', 'Resident Grievance Officer & Legal Counsel', tokens),
                  _buildInfoRow(
                    'Physical Office Address in India',
                    'Sanctuary Legal Operations Desk, Level 4, Tower B, Sector 62, Noida, UP 201309, India',
                    tokens,
                  ),
                  _buildInfoRow('Email Address', 'grievance@urheart.app', tokens),
                  _buildInfoRow('Escalation Legal Desk', 'legal@urheart.app', tokens),
                  _buildInfoRow('Helpline', '+91-120-4567890 (Mon–Fri, 10 AM – 6 PM IST)', tokens),
                  _buildInfoRow('Web Redressal Portal', 'https://urheart.app/grievance', tokens),
                  const Divider(height: 20),
                  Text(
                    'Statutory Service Level Agreements (SLAs)',
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.sansFont,
                      fontSize: 13.0,
                      fontWeight: FontWeight.w600,
                      color: tokens.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 6),
                  _buildBullet(
                    '24-Hour Acknowledgment: Automated dossier tracking number (URH-GRV-...) issued within 24 hours.',
                    tokens,
                  ),
                  _buildBullet(
                    '24-Hour NCII Takedown: Emergency takedown of non-consensual imagery within 24 hours (IT Rules 3(2)(b)).',
                    tokens,
                  ),
                  _buildBullet(
                    '15-Day Final Resolution: Comprehensive written redressal order issued within 15 calendar days.',
                    tokens,
                  ),
                  _buildBullet(
                    'Appellate Forum: Appeal to Central Government Grievance Appellate Committee (https://gac.gov.in) within 30 days.',
                    tokens,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // DPDP Act 2023 Statutory Disclosures
            SanctuaryGlassContainer(
              borderRadius: 16.0,
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionHeader(
                    icon: Icons.verified_user_outlined,
                    title: 'DPDP Act 2023 Statutory Disclosures',
                    subtitle: 'Notice, Consent, Minor Protection & Erasure',
                    tokens: tokens,
                  ),
                  const SizedBox(height: 12),
                  _buildBullet(
                    'Section 6 Purpose Limitation: Data collected strictly for seeker matching and sanctuary safety telemetry. Never sold or rented to data brokers.',
                    tokens,
                  ),
                  _buildBullet(
                    'Section 9 Minor Protection: Strict 18+ adult sanctuary. Under-age access barred via biometric age verification; 365-day hardware hash quarantine on violations.',
                    tokens,
                  ),
                  _buildBullet(
                    'Section 12 Account Incineration: Seekers may trigger irrevocable persona incineration at any time, purging profile, photos, and chat logs permanently.',
                    tokens,
                  ),
                  _buildBullet(
                    'Section 14 Nominee Designation: Seekers may appoint a statutory nominee via Sacred Legal Vault to manage account state in unforeseen events.',
                    tokens,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Safety & Cryptographic Architecture
            SanctuaryGlassContainer(
              borderRadius: 16.0,
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionHeader(
                    icon: Icons.shield_outlined,
                    title: 'Safety & Cryptographic Architecture',
                    subtitle: 'Sanctuary Design & Privacy Safeguards',
                    tokens: tokens,
                  ),
                  const SizedBox(height: 12),
                  _buildBullet('35-pixel Gaussian Modesty Blur on photos until mutual resonance is achieved.', tokens),
                  _buildBullet('10-swipe daily exploration rhythm with circadian slumber to preserve mindfulness.', tokens),
                  _buildBullet('Anti-screenshot FLAG_SECURE window security shielding private chats and media.', tokens),
                  _buildBullet('AES-256-GCM authenticated encryption on Blind Date sanctuary communications.', tokens),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Statutory Policies, Terms & Licenses Tiles
            SanctuaryGlassContainer(
              borderRadius: 16.0,
              padding: const EdgeInsets.symmetric(vertical: 8.0),
              child: Column(
                children: [
                  ListTile(
                    leading: Icon(Icons.description_outlined, color: tokens.textSecondary),
                    title: Text(
                      'Master Terms of Service',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 14.5,
                        fontWeight: FontWeight.w600,
                        color: tokens.textPrimary,
                      ),
                    ),
                    subtitle: Text(
                      'Effective Oct 15, 2026 • IT Rules 2021 Compliant',
                      style: SanctuaryTypography.caption(tokens.textTertiary),
                    ),
                    trailing: Icon(Icons.chevron_right_rounded, color: tokens.textTertiary),
                    onTap: () => _showTermsDialog(context, tokens),
                  ),
                  Divider(height: 1, indent: 56, color: tokens.borderSpecularStart.withValues(alpha: 0.1)),
                  ListTile(
                    leading: Icon(Icons.privacy_tip_outlined, color: tokens.textSecondary),
                    title: Text(
                      'Privacy Policy & Data Notice',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 14.5,
                        fontWeight: FontWeight.w600,
                        color: tokens.textPrimary,
                      ),
                    ),
                    subtitle: Text(
                      'Effective Oct 15, 2026 • DPDP Act 2023 Compliant',
                      style: SanctuaryTypography.caption(tokens.textTertiary),
                    ),
                    trailing: Icon(Icons.chevron_right_rounded, color: tokens.textTertiary),
                    onTap: () => _showPrivacyDialog(context, tokens),
                  ),
                  Divider(height: 1, indent: 56, color: tokens.borderSpecularStart.withValues(alpha: 0.1)),
                  ListTile(
                    leading: Icon(Icons.source_outlined, color: tokens.textSecondary),
                    title: Text(
                      'Open Source Licenses',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 14.5,
                        fontWeight: FontWeight.w600,
                        color: tokens.textPrimary,
                      ),
                    ),
                    subtitle: Text(
                      'Third-party software libraries and notices',
                      style: SanctuaryTypography.caption(tokens.textTertiary),
                    ),
                    trailing: Icon(Icons.chevron_right_rounded, color: tokens.textTertiary),
                    onTap: () {
                      showLicensePage(
                        context: context,
                        applicationName: appName,
                        applicationVersion: '$appVersion ($buildLabel)',
                        applicationLegalese: '© 2026 ASI Verticals Private Limited. All rights reserved.',
                      );
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Footer Copyright
            Center(
              child: Column(
                children: [
                  Text(
                    '© 2026 ASI Verticals Private Limited. All rights reserved.',
                    style: SanctuaryTypography.caption(tokens.textSecondary),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Governed under the Laws of the Republic of India',
                    style: SanctuaryTypography.caption(tokens.textTertiary),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader({
    required IconData icon,
    required String title,
    required String subtitle,
    required SanctuaryGlassTokens tokens,
  }) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(8.0),
          decoration: BoxDecoration(
            color: tokens.glowGold.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(10.0),
          ),
          child: Icon(icon, color: SanctuaryGlassTokens.brandSacredGold, size: 20),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  fontFamily: SanctuaryTypography.serifFont,
                  fontSize: 16.5,
                  fontWeight: FontWeight.w700,
                  color: tokens.textPrimary,
                ),
              ),
              Text(
                subtitle,
                style: TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  fontSize: 11.0,
                  fontWeight: FontWeight.w600,
                  color: tokens.textTertiary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildInfoRow(String label, String value, SanctuaryGlassTokens tokens) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6.0),
      child: RichText(
        text: TextSpan(
          style: SanctuaryTypography.bodySmall(tokens.textSecondary),
          children: [
            TextSpan(
              text: '$label: ',
              style: TextStyle(
                fontWeight: FontWeight.w600,
                color: tokens.textPrimary,
              ),
            ),
            TextSpan(text: value),
          ],
        ),
      ),
    );
  }

  Widget _buildBullet(String text, SanctuaryGlassTokens tokens) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.check_circle_outline_rounded, size: 15, color: tokens.glowPine),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: SanctuaryTypography.bodySmall(tokens.textSecondary),
            ),
          ),
        ],
      ),
    );
  }

  void _showTermsDialog(BuildContext context, SanctuaryGlassTokens tokens) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: tokens.elevatedSurface,
        title: Text(
          'Master Terms of Service',
          style: TextStyle(
            fontFamily: SanctuaryTypography.serifFont,
            color: tokens.textPrimary,
          ),
        ),
        content: SingleChildScrollView(
          child: Text(
            'UR-HEART SANCTUARY MASTER TERMS OF SERVICE\n'
            'Version 1.0 • Effective Date: October 15, 2026\n'
            'Operated by ASI Verticals Private Limited\n\n'
            '1. Acceptance & Age Qualification: By entering UR-Heart Sanctuary, you certify you are 18+ years of age. Under-age access is strictly forbidden.\n\n'
            '2. Modesty Veil & Consensual Unmasking: Photos remain under a 35-pixel Gaussian veil until both seekers affirm mutual resonance. Circumvention of veil security violates these terms.\n\n'
            '3. User Obligations (IT Rules 2021 Rule 3(1)(b)): Seekers agree not to host, display, upload, modify, or transmit content that is obscene, defamatory, invasive of another privacy, or non-consensual.\n\n'
            '4. Safe Harbor & Emergency Takedown: ASI Verticals maintains a 24-hour SLA for non-consensual intimate imagery (NCII) takedown under Rule 3(2)(b).\n\n'
            '5. Governing Law: These terms are governed by the laws of India. Disputes are subject to the exclusive jurisdiction of courts in New Delhi.',
            style: SanctuaryTypography.bodySmall(tokens.textSecondary),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Close', style: TextStyle(color: SanctuaryGlassTokens.brandSacredGold)),
          ),
        ],
      ),
    );
  }

  void _showPrivacyDialog(BuildContext context, SanctuaryGlassTokens tokens) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: tokens.elevatedSurface,
        title: Text(
          'Privacy Policy & Data Notice',
          style: TextStyle(
            fontFamily: SanctuaryTypography.serifFont,
            color: tokens.textPrimary,
          ),
        ),
        content: SingleChildScrollView(
          child: Text(
            'STATUTORY PRIVACY NOTICE & DATA CHARTER\n'
            'Pursuant to DPDP Act 2023 Sections 5 & 6\n'
            'ASI Verticals Private Limited (Data Fiduciary)\n\n'
            '1. Purpose Specification: Your personal data (profile, photo biometric markers, interaction metadata) is processed strictly to facilitate genuine romantic discovery and prevent platform abuse.\n\n'
            '2. Right to Correction and Erasure (§12): You possess the unfettered statutory right to withdraw consent and incinerate your sacred persona at any moment via the Sacred Legal Vault.\n\n'
            '3. Data Retention Schedule: Active persona data is purged immediately upon incineration. Financial ledger summaries are retained for 7 years pursuant to Income Tax Act § 44AB; grievance records for 1 year pursuant to IT Rules 2021.\n\n'
            '4. Resident Grievance Officer (§13): Adv. Vikramaditya Sen, Level 4, Tower B, Sector 62, Noida, UP 201309. Email: grievance@urheart.app.',
            style: SanctuaryTypography.bodySmall(tokens.textSecondary),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Close', style: TextStyle(color: SanctuaryGlassTokens.brandSacredGold)),
          ),
        ],
      ),
    );
  }
}
