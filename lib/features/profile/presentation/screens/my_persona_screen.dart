import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/app_typography.dart';
import '../../../../core/network/sanctuary_http_client.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../../../auth/presentation/controllers/auth_controller.dart';

/// Screen 4: MyPersonaScreen (Main Bottom Nav Tab Index 4)
/// Seeker's own profile dashboard, stats, and primary gateway to Settings and Legal Vault.
class MyPersonaScreen extends ConsumerStatefulWidget {
  const MyPersonaScreen({super.key});

  @override
  ConsumerState<MyPersonaScreen> createState() => _MyPersonaScreenState();
}

class _MyPersonaScreenState extends ConsumerState<MyPersonaScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  Map<String, dynamic> _profile = {};

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final client = ref.read(sanctuaryHttpClientProvider);
      final res = await client.get('/api/v1/auth/me');
      final data = res['data'];
      if (!mounted) return;
      setState(() {
        if (data is Map<String, dynamic>) {
          _profile = data;
        } else if (data is Map) {
          _profile = Map<String, dynamic>.from(data);
        }
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _errorMessage = 'Unable to load seeker profile. Please check connection and retry.';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();
    final currentUser = ref.watch(currentUserProvider);

    final fullName = _profile['full_name']?.toString() ?? 'Seeker';
    final role = _profile['role']?.toString() ?? currentUser?.role ?? 'user';
    final kycStatus = _profile['kyc_status'] == true;
    final streakCount = _profile['streak_count'] ?? 0;
    final subscriptionTier = _profile['subscription_tier']?.toString() ?? 'free';
    final avatarUrl = _profile['avatar_url']?.toString();
    final isAdmin = role == 'superadmin' || role == 'moderator';

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: SafeArea(
        bottom: false,
        child: _isLoading
            ? Center(
                child: CircularProgressIndicator(
                  valueColor: AlwaysStoppedAnimation<Color>(tokens.glowTerracotta),
                ),
              )
            : (_errorMessage != null && _profile.isEmpty)
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24.0),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.cloud_off_rounded, size: 64, color: tokens.textSecondary),
                          const SizedBox(height: 16),
                          Text(
                            _errorMessage!,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontFamily: SanctuaryTypography.sansFont,
                              color: tokens.textSecondary,
                              fontSize: 14,
                            ),
                          ),
                          const SizedBox(height: 20),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: tokens.glowTerracotta,
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            onPressed: _loadProfile,
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                  )
                : RefreshIndicator(
                onRefresh: _loadProfile,
                color: tokens.glowTerracotta,
                backgroundColor: tokens.elevatedSurface,
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 100),
                  children: [
                    // 1. Top Bar
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'My Persona',
                          style: SanctuaryTypography.titleH1(tokens.textPrimary, isDark: isDark),
                        ),
                        IconButton(
                          icon: Icon(Icons.settings_outlined, color: tokens.textPrimary),
                          onPressed: () => context.push('/settings'),
                        ),
                      ],
                    ),

                    if (_errorMessage != null && _profile.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      SanctuaryGlassContainer(
                        borderRadius: 12,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        child: Row(
                          children: [
                            const Icon(Icons.warning_amber_rounded, color: Colors.amber, size: 20),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                _errorMessage!,
                                style: TextStyle(
                                  fontFamily: SanctuaryTypography.sansFont,
                                  color: tokens.textSecondary,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                            TextButton(
                              onPressed: _loadProfile,
                              child: Text('Retry', style: TextStyle(color: tokens.glowTerracotta, fontSize: 12)),
                            ),
                          ],
                        ),
                      ),
                    ],

                    const SizedBox(height: 20),

                    // 2. Persona Card
                    SanctuaryGlassContainer(
                      borderRadius: 24,
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        children: [
                          CircleAvatar(
                            radius: 44,
                            backgroundColor: tokens.glowTerracotta.withValues(alpha: 0.2),
                            backgroundImage: (avatarUrl != null && avatarUrl.isNotEmpty)
                                ? NetworkImage(avatarUrl)
                                : null,
                            child: (avatarUrl == null || avatarUrl.isEmpty)
                                ? Text(
                                    fullName.isNotEmpty ? fullName[0].toUpperCase() : 'S',
                                    style: TextStyle(
                                      fontSize: 34,
                                      fontWeight: FontWeight.bold,
                                      color: tokens.textPrimary,
                                    ),
                                  )
                                : null,
                          ),
                          const SizedBox(height: 14),
                          Text(
                            fullName,
                            style: SanctuaryTypography.titleH2(tokens.textPrimary, isDark: isDark),
                          ),
                          const SizedBox(height: 6),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: kycStatus
                                      ? tokens.glowPine.withValues(alpha: 0.2)
                                      : Colors.amber.withValues(alpha: 0.2),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      kycStatus ? Icons.verified_user_rounded : Icons.pending_outlined,
                                      size: 14,
                                      color: kycStatus ? tokens.glowPine : Colors.amber,
                                    ),
                                    const SizedBox(width: 4),
                                    Text(
                                      kycStatus ? 'KYC Verified' : 'KYC Pending',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                        color: kycStatus ? tokens.glowPine : Colors.amber,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: tokens.glowTerracotta.withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  'Tier: ${subscriptionTier.toUpperCase()}',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: tokens.glowTerracotta,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                            children: [
                              Column(
                                children: [
                                  Text(
                                    '$streakCount',
                                    style: TextStyle(
                                      fontFamily: SanctuaryTypography.sansFont,
                                      fontSize: 20,
                                      fontWeight: FontWeight.bold,
                                      color: tokens.textPrimary,
                                    ),
                                  ),
                                  Text(
                                    'Streak Days',
                                    style: SanctuaryTypography.caption(tokens.textSecondary),
                                  ),
                                ],
                              ),
                              Container(height: 24, width: 1, color: tokens.borderSpecularEnd),
                              Column(
                                children: [
                                  Text(
                                    role.toUpperCase(),
                                    style: TextStyle(
                                      fontFamily: SanctuaryTypography.sansFont,
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                      color: tokens.textPrimary,
                                    ),
                                  ),
                                  Text(
                                    'Role',
                                    style: SanctuaryTypography.caption(tokens.textSecondary),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 24),

                    // 3. Navigation Actions Reconnecting Orphaned Routes
                    Text(
                      'Sanctuary Governance & Management',
                      style: SanctuaryTypography.bodyMedium(tokens.textPrimary),
                    ),
                    const SizedBox(height: 12),

                    // Legal Vault Tile
                    SanctuaryGlassContainer(
                      borderRadius: 16,
                      padding: const EdgeInsets.all(16),
                      onTap: () => context.push('/vault'),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: tokens.glowPine.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Icon(Icons.shield_outlined, color: tokens.glowPine),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'DPDP Legal Vault',
                                  style: TextStyle(
                                    fontFamily: SanctuaryTypography.sansFont,
                                    fontWeight: FontWeight.w600,
                                    fontSize: 15,
                                    color: tokens.textPrimary,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  'Section 14 Nominee, Data Portability & Grievances',
                                  style: SanctuaryTypography.caption(tokens.textSecondary),
                                ),
                              ],
                            ),
                          ),
                          Icon(Icons.chevron_right_rounded, color: tokens.textTertiary),
                        ],
                      ),
                    ),

                    const SizedBox(height: 10),

                    // Settings Tile
                    SanctuaryGlassContainer(
                      borderRadius: 16,
                      padding: const EdgeInsets.all(16),
                      onTap: () => context.push('/settings'),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: tokens.glowTerracotta.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Icon(Icons.tune_rounded, color: tokens.glowTerracotta),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Privacy & Settings',
                                  style: TextStyle(
                                    fontFamily: SanctuaryTypography.sansFont,
                                    fontWeight: FontWeight.w600,
                                    fontSize: 15,
                                    color: tokens.textPrimary,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  'Theme, privacy modes & Section 12 Incineration',
                                  style: SanctuaryTypography.caption(tokens.textSecondary),
                                ),
                              ],
                            ),
                          ),
                          Icon(Icons.chevron_right_rounded, color: tokens.textTertiary),
                        ],
                      ),
                    ),

                    const SizedBox(height: 10),

                    // Edit Profile Setup
                    SanctuaryGlassContainer(
                      borderRadius: 16,
                      padding: const EdgeInsets.all(16),
                      onTap: () => context.push('/profile-setup'),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: tokens.glowGold.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Icon(Icons.edit_note_rounded, color: tokens.glowGold),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Edit Profile & Media',
                                  style: TextStyle(
                                    fontFamily: SanctuaryTypography.sansFont,
                                    fontWeight: FontWeight.w600,
                                    fontSize: 15,
                                    color: tokens.textPrimary,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  'Moments, Voice Spark & Contact Bridge',
                                  style: SanctuaryTypography.caption(tokens.textSecondary),
                                ),
                              ],
                            ),
                          ),
                          Icon(Icons.chevron_right_rounded, color: tokens.textTertiary),
                        ],
                      ),
                    ),

                    if (isAdmin) ...[
                      const SizedBox(height: 10),
                      SanctuaryGlassContainer(
                        borderRadius: 16,
                        padding: const EdgeInsets.all(16),
                        onTap: () => context.push('/admin/kyc-desk'),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: Colors.deepPurple.withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Icon(Icons.admin_panel_settings_rounded, color: Colors.purpleAccent),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Superadmin KYC Desk',
                                    style: TextStyle(
                                      fontFamily: SanctuaryTypography.sansFont,
                                      fontWeight: FontWeight.w600,
                                      fontSize: 15,
                                      color: tokens.textPrimary,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    'Adjudicate escalated biometric liveness cases',
                                    style: SanctuaryTypography.caption(tokens.textSecondary),
                                  ),
                                ],
                              ),
                            ),
                            Icon(Icons.chevron_right_rounded, color: tokens.textTertiary),
                          ],
                        ),
                      ),
                    ],

                    const SizedBox(height: 10),

                    // App Disclosures
                    SanctuaryGlassContainer(
                      borderRadius: 16,
                      padding: const EdgeInsets.all(16),
                      onTap: () => context.push('/app-info'),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: tokens.textSecondary.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Icon(Icons.info_outline_rounded, color: tokens.textSecondary),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'App Information',
                                  style: TextStyle(
                                    fontFamily: SanctuaryTypography.sansFont,
                                    fontWeight: FontWeight.w600,
                                    fontSize: 15,
                                    color: tokens.textPrimary,
                                  ),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  'Version, Terms of Service & Privacy Disclosures',
                                  style: SanctuaryTypography.caption(tokens.textSecondary),
                                ),
                              ],
                            ),
                          ),
                          Icon(Icons.chevron_right_rounded, color: tokens.textTertiary),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
      ),
    );
  }
}
