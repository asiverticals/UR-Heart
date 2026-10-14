import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/constants/app_typography.dart';
import '../../../../core/services/window_security_service.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/glass_veil_widget.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../../../feed/domain/models/discovery_profile.dart';
import '../controllers/seeker_profile_controller.dart';

class SeekerProfileDetailScreen extends ConsumerStatefulWidget {
  final String userId;
  final DiscoveryProfile? initialProfile;

  const SeekerProfileDetailScreen({
    super.key,
    required this.userId,
    this.initialProfile,
  });

  @override
  ConsumerState<SeekerProfileDetailScreen> createState() =>
      _SeekerProfileDetailScreenState();
}

class _SeekerProfileDetailScreenState
    extends ConsumerState<SeekerProfileDetailScreen> {
  late final PageController _pageController;
  int _activePhotoIndex = 0;

  bool _isPlayingVoiceSpark = false;
  double _voiceSparkProgress = 0.0;
  Timer? _voiceTimer;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
    // Hardware Window Protection (FLAG_SECURE = 8192)
    WindowSecurityService.enforceWindowProtection('/seeker-detail');
    if (widget.initialProfile != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          ref
              .read(seekerProfileControllerProvider(widget.userId).notifier)
              .setProfile(widget.initialProfile!);
        }
      });
    }
  }

  @override
  void dispose() {
    _voiceTimer?.cancel();
    _pageController.dispose();
    // Relax hardware window protection upon exiting detail view
    WindowSecurityService.relaxWindowProtection();
    super.dispose();
  }

  void _toggleVoiceSpark() {
    if (_isPlayingVoiceSpark) {
      _voiceTimer?.cancel();
      setState(() {
        _isPlayingVoiceSpark = false;
        _voiceSparkProgress = 0.0;
      });
    } else {
      setState(() {
        _isPlayingVoiceSpark = true;
        _voiceSparkProgress = 0.0;
      });
      const intervalMs = 100;
      const totalDurationMs = 7000;
      const step = intervalMs / totalDurationMs;

      _voiceTimer = Timer.periodic(const Duration(milliseconds: intervalMs), (timer) {
        if (!mounted) {
          timer.cancel();
          return;
        }
        setState(() {
          _voiceSparkProgress += step;
          if (_voiceSparkProgress >= 1.0) {
            _voiceSparkProgress = 0.0;
            _isPlayingVoiceSpark = false;
            timer.cancel();
          }
        });
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();
    final profileState = ref.watch(seekerProfileControllerProvider(widget.userId));
    final profile = profileState.profile ?? widget.initialProfile;

    if (profileState.isLoading && profile == null) {
      return Scaffold(
        backgroundColor: tokens.backgroundCanvas,
        body: Center(
          child: CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(
              isDark
                  ? SanctuaryGlassTokens.brandSacredGold
                  : SanctuaryGlassTokens.brandPine,
            ),
          ),
        ),
      );
    }

    if (profile == null) {
      return Scaffold(
        backgroundColor: tokens.backgroundCanvas,
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          leading: IconButton(
            icon: Icon(Icons.arrow_back_rounded, color: tokens.textPrimary),
            onPressed: () => Navigator.of(context).maybePop(),
          ),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.person_off_outlined,
                  size: 54,
                  color: SanctuaryGlassTokens.alertRed,
                ),
                const SizedBox(height: 16),
                Text(
                  profileState.errorMessage ?? "Seeker profile unavailable.",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 14,
                    color: tokens.textSecondary,
                  ),
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: SanctuaryGlassTokens.brandPine,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: () => ref
                      .read(seekerProfileControllerProvider(widget.userId).notifier)
                      .loadProfile(widget.userId),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final initialPhotos = widget.initialProfile?.photos ?? const <String>[];
    final photos = profile.photos.isNotEmpty
        ? profile.photos
        : (initialPhotos.isNotEmpty
            ? initialPhotos
            : (profile.avatarUrl != null
                ? [profile.avatarUrl!]
                : (widget.initialProfile?.avatarUrl != null
                    ? [widget.initialProfile!.avatarUrl!]
                    : <String>[])));

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: Padding(
          padding: const EdgeInsets.all(8.0),
          child: CircleAvatar(
            backgroundColor: Colors.black.withValues(alpha: 0.45),
            child: IconButton(
              icon: const Icon(Icons.arrow_back_rounded, color: Colors.white, size: 20),
              onPressed: () => Navigator.of(context).maybePop(),
            ),
          ),
        ),
        actions: [
          if (profile.kycStatus)
            Padding(
              padding: const EdgeInsets.only(right: 16.0),
              child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 4.0),
                  decoration: BoxDecoration(
                    color: SanctuaryGlassTokens.brandPine.withValues(alpha: 0.85),
                    borderRadius: BorderRadius.circular(12.0),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.3)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.verified_rounded, size: 14, color: Colors.white),
                      SizedBox(width: 4),
                      Text(
                        'Verified Seeker',
                        style: TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 1. Dynamic Hero Photo Carousel with 35px GlassVeilWidget
            SizedBox(
              height: 480,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  // Photo PageView inside 35px Gaussian Blur Veil
                  GlassVeilWidget(
                    isVeiled: profileState.isPhotoVeiled,
                    veilBlur: 35.0,
                    seekerFirstName: profile.fullName.split(' ').first,
                    underlyingImage: photos.isNotEmpty
                        ? PageView.builder(
                            controller: _pageController,
                            itemCount: photos.length,
                            onPageChanged: (idx) =>
                                setState(() => _activePhotoIndex = idx),
                            itemBuilder: (context, index) {
                              return Image.network(
                                photos[index],
                                fit: BoxFit.cover,
                                width: double.infinity,
                                height: double.infinity,
                                errorBuilder: (_, __, ___) => Container(
                                  color: tokens.backgroundCanvas,
                                  child: const Center(
                                    child: Icon(Icons.broken_image_rounded, size: 48),
                                  ),
                                ),
                              );
                            },
                          )
                        : Container(
                            color: tokens.glassTintSecondary,
                            child: const Center(
                              child: Icon(Icons.person, size: 80),
                            ),
                          ),
                  ),

                  // Optical bottom gradient for readability
                  Positioned.fill(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          stops: const [0.0, 0.5, 0.85, 1.0],
                          colors: [
                            Colors.black.withValues(alpha: 0.30),
                            Colors.transparent,
                            Colors.black.withValues(alpha: 0.65),
                            tokens.backgroundCanvas,
                          ],
                        ),
                      ),
                    ),
                  ),

                  // Carousel Indicators
                  if (photos.length > 1)
                    Positioned(
                      bottom: 24,
                      left: 0,
                      right: 0,
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: List.generate(
                          photos.length,
                          (i) => AnimatedContainer(
                            duration: const Duration(milliseconds: 250),
                            margin: const EdgeInsets.symmetric(horizontal: 3.0),
                            width: _activePhotoIndex == i ? 18.0 : 6.0,
                            height: 6.0,
                            decoration: BoxDecoration(
                              color: _activePhotoIndex == i
                                  ? SanctuaryGlassTokens.brandSacredGold
                                  : Colors.white.withValues(alpha: 0.4),
                              borderRadius: BorderRadius.circular(3.0),
                            ),
                          ),
                        ),
                      ),
                    ),

                  // Floating Modesty Shield Banner (When Veiled)
                  if (profileState.isPhotoVeiled)
                    Positioned(
                      left: 16.0,
                      right: 16.0,
                      bottom: 40.0,
                      child: _buildModestyShieldBanner(
                        context,
                        profileState,
                        tokens,
                        isDark,
                      ),
                    ),
                ],
              ),
            ),

            // 2. Profile Details & Editorial Sheet
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 12.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Full Name & Age
                  Text(
                    '${profile.fullName}, ${profile.age}',
                    style: SanctuaryTypography.titleH1(tokens.textPrimary, isDark: isDark),
                  ),
                  const SizedBox(height: 6),

                  // Profession & Education
                  if (profile.profession.isNotEmpty || profile.education.isNotEmpty)
                    Text(
                      [
                        if (profile.profession.isNotEmpty) profile.profession,
                        if (profile.education.isNotEmpty) profile.education,
                      ].join(' • '),
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: tokens.textSecondary,
                      ),
                    ),
                  const SizedBox(height: 14),

                  // Badges: Proximity & Mindful Streak
                  Wrap(
                    spacing: 8.0,
                    runSpacing: 8.0,
                    children: [
                      // Distance Chip
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 6.0),
                        decoration: BoxDecoration(
                          color: tokens.glassTintPrimary,
                          borderRadius: BorderRadius.circular(16.0),
                          border: Border.all(
                            color: tokens.borderSpecularStart.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(
                              Icons.near_me_rounded,
                              size: 14,
                              color: SanctuaryGlassTokens.brandSacredGold,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              profile.distanceKm != null
                                  ? '${profile.locationName} • ~${profile.distanceKm!.toStringAsFixed(1)} km away'
                                  : profile.locationName,
                              style: TextStyle(
                                fontFamily: SanctuaryTypography.sansFont,
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                                color: tokens.textPrimary,
                              ),
                            ),
                          ],
                        ),
                      ),

                      // Mindful Streak Badge
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 6.0),
                        decoration: BoxDecoration(
                          color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(16.0),
                          border: Border.all(
                            color: SanctuaryGlassTokens.brandTerracottaGlow.withValues(alpha: 0.4),
                          ),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(
                              Icons.local_fire_department_rounded,
                              size: 14,
                              color: SanctuaryGlassTokens.brandTerracottaGlow,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              '${profile.streakCount}d Mindful Streak',
                              style: const TextStyle(
                                fontFamily: SanctuaryTypography.sansFont,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: SanctuaryGlassTokens.brandTerracottaGlow,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // 3. Editorial Bio Prose Card
                  if (profile.bio.isNotEmpty) ...[
                    Text(
                      'Resonance Prose',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.8,
                        color: tokens.textTertiary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    SanctuaryGlassContainer(
                      borderRadius: 18.0,
                      blurSigma: 10.0,
                      padding: const EdgeInsets.all(20.0),
                      child: Text(
                        '"${profile.bio}"',
                        style: SanctuaryTypography.quote(
                          tokens.textPrimary,
                          isDark: isDark,
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],

                  // 4. 7-Second Voice Spark Waveform Player
                  if (profile.voiceSparkUrl != null) ...[
                    Text(
                      '7-Second Voice Spark',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.8,
                        color: tokens.textTertiary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    _buildVoiceSparkPlayer(tokens, profile, isDark),
                    const SizedBox(height: 32),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildModestyShieldBanner(
    BuildContext context,
    SeekerProfileState state,
    SanctuaryGlassTokens tokens,
    bool isDark,
  ) {
    final isPending = state.revealStatus == 'pending';
    final isDeclined = state.revealStatus == 'declined';

    return SanctuaryGlassContainer(
      borderRadius: 22.0,
      blurSigma: 16.0,
      padding: const EdgeInsets.all(18.0),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10.0),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
                ),
                child: const Icon(
                  Icons.visibility_off_outlined,
                  size: 24,
                  color: SanctuaryGlassTokens.brandSacredGold,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      isPending
                          ? 'Reveal Request Pending'
                          : (isDeclined
                              ? 'Request Declined'
                              : 'Veiled in Sacred Modesty'),
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: tokens.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      isPending
                          ? 'Awaiting gentle consent from seeker.'
                          : (isDeclined
                              ? 'Reveal was politely declined with grace.'
                              : 'Photos remain blurred until bilateral consent or instant unmasking.'),
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 12,
                        color: tokens.textSecondary,
                        height: 1.3,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              // 1. Request Photo Reveal Button
              Expanded(
                child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: tokens.textPrimary,
                    side: BorderSide(
                      color: isPending
                          ? tokens.textTertiary.withValues(alpha: 0.3)
                          : SanctuaryGlassTokens.brandSacredGold,
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 11),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14.0),
                    ),
                  ),
                  onPressed: (isPending || state.isProcessingAction)
                      ? null
                      : () => ref
                          .read(seekerProfileControllerProvider(widget.userId).notifier)
                          .requestPhotoReveal(),
                  icon: state.isProcessingAction && !isPending
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(
                          isPending ? Icons.hourglass_top_rounded : Icons.lock_open_rounded,
                          size: 16,
                          color: isPending
                              ? tokens.textTertiary
                              : SanctuaryGlassTokens.brandSacredGold,
                        ),
                  label: Text(
                    isPending ? 'Request Sent' : 'Request Reveal',
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.sansFont,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: isPending ? tokens.textTertiary : tokens.textPrimary,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),

              // 2. Micro-Perk Instant Unveil (₹39)
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: SanctuaryGlassTokens.brandSacredGold,
                  foregroundColor: Colors.black,
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14.0),
                  ),
                ),
                onPressed: state.isProcessingAction
                    ? null
                    : () => ref
                        .read(seekerProfileControllerProvider(widget.userId).notifier)
                        .unlockWithPerk(),
                icon: const Icon(Icons.flash_on_rounded, size: 16, color: Colors.black),
                label: const Text(
                  'Instant Unveil (₹39)',
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: Colors.black,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildVoiceSparkPlayer(
    SanctuaryGlassTokens tokens,
    DiscoveryProfile profile,
    bool isDark,
  ) {
    return SanctuaryGlassContainer(
      borderRadius: 18.0,
      blurSigma: 12.0,
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              InkWell(
                onTap: _toggleVoiceSpark,
                borderRadius: BorderRadius.circular(22.0),
                child: Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: SanctuaryGlassTokens.brandTerracotta,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.4),
                        blurRadius: 8.0,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Icon(
                    _isPlayingVoiceSpark ? Icons.stop_rounded : Icons.play_arrow_rounded,
                    color: Colors.white,
                    size: 26,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      profile.voiceSparkPrompt ?? 'Spoken Reflection',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: tokens.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      _isPlayingVoiceSpark
                          ? 'Playing 7.0s authentic voice spark...'
                          : 'Listen to their authentic voice spark',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 11.5,
                        color: tokens.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Simulated waveform / audio progress bar
          ClipRRect(
            borderRadius: BorderRadius.circular(4.0),
            child: LinearProgressIndicator(
              value: _voiceSparkProgress,
              backgroundColor: tokens.borderSpecularStart.withValues(alpha: 0.25),
              valueColor: const AlwaysStoppedAnimation<Color>(
                SanctuaryGlassTokens.brandSacredGold,
              ),
              minHeight: 4.0,
            ),
          ),
        ],
      ),
    );
  }
}
