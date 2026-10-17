import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/glass_veil_widget.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../../domain/models/discovery_profile.dart';
import '../controllers/feed_controller.dart';

/// Screen 6: FeedScreen (/main - Tab 0: Discovery Deck)
/// Mindful 10-swipe discovery deck enforcing the 35px photo blur veil,
/// DPDP neighborhood coordinate fuzzing, and reciprocal action controls.
class FeedScreen extends ConsumerStatefulWidget {
  const FeedScreen({super.key});

  @override
  ConsumerState<FeedScreen> createState() => _FeedScreenState();
}

class _FeedScreenState extends ConsumerState<FeedScreen> {
  bool _isPlayingVoiceSpark = false;
  double _voiceSparkProgress = 0.0;
  Timer? _voiceSparkTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(feedControllerProvider.notifier).fetchDeck();
    });
  }

  @override
  void dispose() {
    _voiceSparkTimer?.cancel();
    super.dispose();
  }

  void _toggleVoiceSpark() {
    if (_isPlayingVoiceSpark) {
      _voiceSparkTimer?.cancel();
      setState(() {
        _isPlayingVoiceSpark = false;
        _voiceSparkProgress = 0.0;
      });
    } else {
      setState(() {
        _isPlayingVoiceSpark = true;
        _voiceSparkProgress = 0.0;
      });
      _voiceSparkTimer?.cancel();
      _voiceSparkTimer = Timer.periodic(const Duration(milliseconds: 100), (timer) {
        if (!mounted) {
          timer.cancel();
          return;
        }
        setState(() {
          _voiceSparkProgress = (_voiceSparkProgress + 0.1).clamp(0.0, 7.0);
        });
        if (_voiceSparkProgress >= 7.0) {
          timer.cancel();
          setState(() {
            _isPlayingVoiceSpark = false;
            _voiceSparkProgress = 0.0;
          });
        }
      });
    }
  }

  Future<void> _showDirectLetterDialog(
    BuildContext context,
    DiscoveryProfile profile,
    SanctuaryGlassTokens tokens,
    bool isDark,
  ) async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return _DirectLetterDialog(
          profile: profile,
          tokens: tokens,
          isDark: isDark,
          onSend: (note) {
            ref.read(feedControllerProvider.notifier).handleSwipe(
                  profile.id,
                  'like',
                  directLetter: note,
                );
          },
        );
      },
    );
  }

  void _showMutualMatchDialog(
    BuildContext context,
    String matchId,
    SanctuaryGlassTokens tokens,
    bool isDark,
  ) {
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return Dialog(
          backgroundColor: Colors.transparent,
          insetPadding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: SanctuaryGlassContainer(
            borderRadius: 24.0,
            blurSigma: 20.0,
            padding: const EdgeInsets.all(24.0),
            customTint: isDark
                ? const Color(0x33C85A32)
                : const Color(0x26C85A32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.favorite_rounded,
                  color: SanctuaryGlassTokens.brandTerracottaGlow,
                  size: 56,
                ),
                const SizedBox(height: 16),
                Text(
                  'Divine Resonance Ignited',
                  textAlign: TextAlign.center,
                  style: SanctuaryTypography.titleH1(
                    tokens.textPrimary,
                    isDark: isDark,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'You and your fellow seeker have mutually resonated. A sacred contact reveal token has been provisioned.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 14,
                    height: 1.4,
                    color: tokens.textSecondary,
                  ),
                ),
                const SizedBox(height: 24),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: SanctuaryGlassTokens.brandTerracotta,
                    foregroundColor: Colors.white,
                    minimumSize: const Size.fromHeight(48),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16.0),
                    ),
                  ),
                  onPressed: () {
                    ref.read(feedControllerProvider.notifier).clearMatch();
                    Navigator.of(dialogContext).pop();
                  },
                  child: const Text(
                    'Continue In Sanctuary',
                    style: TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final feedState = ref.watch(feedControllerProvider);
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    // Listen for mutual matches
    ref.listen<FeedState>(feedControllerProvider, (previous, next) {
      if (next.matchedId != null &&
          (previous == null || previous.matchedId != next.matchedId)) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) {
            _showMutualMatchDialog(context, next.matchedId!, tokens, isDark);
          }
        });
      }
    });

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: SafeArea(
        child: Column(
          children: [
            // 1. Top Bar: Mindful Quota Pill & Streaks
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
              child: _buildTopMindfulBar(feedState, tokens, isDark),
            ),

            if (feedState.errorMessage != null && feedState.profiles.isNotEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 4.0),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 8.0),
                  decoration: BoxDecoration(
                    color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10.0),
                    border: Border.all(
                      color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.4),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline, color: SanctuaryGlassTokens.alertRed, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          feedState.errorMessage!,
                          style: const TextStyle(
                            color: SanctuaryGlassTokens.alertRed,
                            fontSize: 12,
                          ),
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, size: 16),
                        color: SanctuaryGlassTokens.alertRed,
                        onPressed: () => ref.read(feedControllerProvider.notifier).clearError(),
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(),
                      ),
                    ],
                  ),
                ),
              ),

            // 2. Central Discovery Deck
            Expanded(
              child: _buildCentralDeck(feedState, tokens, isDark),
            ),

            // 3. Action Deck Controls (Only shown when active profile is loaded)
            if (feedState.profiles.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 16.0, top: 8.0),
                child: _buildActionDeckControls(
                  feedState.profiles.first,
                  feedState.swipesRemaining,
                  feedState.isSwiping,
                  tokens,
                  isDark,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildTopMindfulBar(
    FeedState feedState,
    SanctuaryGlassTokens tokens,
    bool isDark,
  ) {
    return SanctuaryGlassContainer(
      borderRadius: 20.0,
      blurSigma: 12.0,
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Mindful Quota Pill
          Row(
            children: [
              Icon(
                Icons.spa_rounded,
                size: 20,
                color: feedState.swipesRemaining > 0
                    ? SanctuaryGlassTokens.brandPine
                    : SanctuaryGlassTokens.brandTerracotta,
              ),
              const SizedBox(width: 8),
              Text(
                'Swipes Remaining: ${feedState.swipesRemaining}/10',
                style: TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: tokens.textPrimary,
                ),
              ),
            ],
          ),

          // Streak Counter & Refresh Action
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
                decoration: BoxDecoration(
                  color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12.0),
                  border: Border.all(
                    color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.3),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.local_fire_department_rounded,
                      size: 16,
                      color: SanctuaryGlassTokens.brandTerracottaGlow,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      feedState.profiles.isNotEmpty
                          ? '${feedState.profiles.first.streakCount}d'
                          : '0d',
                      style: const TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: SanctuaryGlassTokens.brandTerracottaGlow,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              InkWell(
                onTap: feedState.isLoading
                    ? null
                    : () => ref.read(feedControllerProvider.notifier).fetchDeck(),
                borderRadius: BorderRadius.circular(16.0),
                child: Padding(
                  padding: const EdgeInsets.all(4.0),
                  child: Icon(
                    Icons.refresh_rounded,
                    size: 20,
                    color: tokens.textSecondary,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildCentralDeck(
    FeedState feedState,
    SanctuaryGlassTokens tokens,
    bool isDark,
  ) {
    if (feedState.isLoading && feedState.profiles.isEmpty) {
      return Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(
            isDark
                ? SanctuaryGlassTokens.brandTerracottaGlow
                : SanctuaryGlassTokens.brandPine,
          ),
        ),
      );
    }

    if (feedState.profiles.isEmpty) {
      return _buildEmptyDeckState(feedState, tokens, isDark);
    }

    final topProfile = feedState.profiles.first;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Background card for stack depth if 2+ profiles exist
          if (feedState.profiles.length > 1)
            Transform.translate(
              offset: const Offset(0, 14),
              child: Transform.scale(
                scale: 0.94,
                child: Opacity(
                  opacity: 0.55,
                  child: SanctuaryGlassContainer(
                    borderRadius: 24.0,
                    blurSigma: 8.0,
                    padding: EdgeInsets.zero,
                    child: Container(
                      color: tokens.glassTintSecondary,
                    ),
                  ),
                ),
              ),
            ),

          // Top active discovery card
          _buildDiscoveryCard(topProfile, tokens, isDark),
        ],
      ),
    );
  }

  Widget _buildEmptyDeckState(
    FeedState feedState,
    SanctuaryGlassTokens tokens,
    bool isDark,
  ) {
    if (feedState.errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: SanctuaryGlassContainer(
            borderRadius: 24.0,
            blurSigma: 16.0,
            padding: const EdgeInsets.all(28.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.info_outline_rounded,
                  size: 52,
                  color: SanctuaryGlassTokens.alertRed,
                ),
                const SizedBox(height: 18),
                Text(
                  "Discovery Paused",
                  textAlign: TextAlign.center,
                  style: SanctuaryTypography.titleH2(
                    tokens.textPrimary,
                    isDark: isDark,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  feedState.errorMessage!,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 14,
                    height: 1.45,
                    color: tokens.textSecondary,
                  ),
                ),
                const SizedBox(height: 24),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: SanctuaryGlassTokens.brandPine,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16.0),
                    ),
                  ),
                  onPressed: () => ref.read(feedControllerProvider.notifier).fetchDeck(),
                  icon: const Icon(Icons.refresh_rounded, size: 18),
                  label: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24.0),
        child: SanctuaryGlassContainer(
          borderRadius: 24.0,
          blurSigma: 16.0,
          padding: const EdgeInsets.all(28.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.nightlight_round,
                size: 52,
                color: isDark
                    ? SanctuaryGlassTokens.brandSacredGold
                    : SanctuaryGlassTokens.brandPine,
              ),
              const SizedBox(height: 18),
              Text(
                "You have met today's rhythm.",
                textAlign: TextAlign.center,
                style: SanctuaryTypography.titleH2(
                  tokens.textPrimary,
                  isDark: isDark,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                "Return tomorrow or complete a mindful reflection in the Growth Hub.",
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  fontSize: 14,
                  height: 1.45,
                  color: tokens.textSecondary,
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: SanctuaryGlassTokens.brandPine,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16.0),
                  ),
                ),
                onPressed: () => ref.read(feedControllerProvider.notifier).fetchDeck(),
                icon: const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('Check Again'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDiscoveryCard(
    DiscoveryProfile profile,
    SanctuaryGlassTokens tokens,
    bool isDark,
  ) {
    final photoUrl = profile.photos.isNotEmpty ? profile.photos.first : profile.avatarUrl;

    Widget photoWidget;
    if (photoUrl != null && photoUrl.startsWith('http')) {
      photoWidget = Image.network(
        photoUrl,
        fit: BoxFit.cover,
        errorBuilder: (context, error, stackTrace) => _buildPlaceholderPhoto(tokens),
        loadingBuilder: (context, child, loadingProgress) {
          if (loadingProgress == null) return child;
          return _buildPlaceholderPhoto(tokens);
        },
      );
    } else {
      photoWidget = _buildPlaceholderPhoto(tokens);
    }

    return GestureDetector(
      onTap: () => context.push(
        '/seeker-detail?userId=${profile.id}',
        extra: profile,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24.0),
        child: SanctuaryGlassContainer(
        borderRadius: 24.0,
        blurSigma: 12.0,
        padding: EdgeInsets.zero,
        child: Stack(
          fit: StackFit.expand,
          children: [
            // 1. Photo with GlassVeilWidget modesty blur (35px default)
            GlassVeilWidget(
              underlyingImage: photoWidget,
              isVeiled: profile.isPhotoVeiled,
              seekerFirstName: profile.fullName,
            ),

            // 2. Optical Gradient Overlay protecting text readability
            Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  stops: const [0.0, 0.45, 0.85, 1.0],
                  colors: [
                    Colors.black.withValues(alpha: 0.25),
                    Colors.transparent,
                    Colors.black.withValues(alpha: 0.70),
                    Colors.black.withValues(alpha: 0.92),
                  ],
                ),
              ),
            ),

            // 3. Top Badges: Distance & KYC Status
            Positioned(
              top: 16.0,
              left: 16.0,
              right: 16.0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // DPDP Fuzzed Distance Chip
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 6.0),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.45),
                      borderRadius: BorderRadius.circular(16.0),
                      border: Border.all(
                        color: Colors.white.withValues(alpha: 0.25),
                        width: 0.8,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.near_me_rounded,
                          size: 13,
                          color: SanctuaryGlassTokens.brandSacredGold,
                        ),
                        const SizedBox(width: 5),
                        Text(
                          profile.distanceKm != null
                              ? '${profile.locationName} • ~${profile.distanceKm!.toStringAsFixed(1)} km away'
                              : profile.locationName,
                          style: const TextStyle(
                            fontFamily: SanctuaryTypography.sansFont,
                            fontSize: 11.5,
                            fontWeight: FontWeight.w500,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // KYC Badge
                  if (profile.kycStatus)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
                      decoration: BoxDecoration(
                        color: SanctuaryGlassTokens.brandPine.withValues(alpha: 0.75),
                        borderRadius: BorderRadius.circular(12.0),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.3),
                          width: 0.8,
                        ),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.verified_rounded,
                            size: 14,
                            color: Colors.white,
                          ),
                          SizedBox(width: 4),
                          Text(
                            'Verified',
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
                ],
              ),
            ),

            // 4. Bottom Prose Content
            Positioned(
              left: 20.0,
              right: 20.0,
              bottom: 20.0,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Seeker Name & Age
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          '${profile.fullName}, ${profile.age}',
                          style: SanctuaryTypography.titleH1(
                            Colors.white,
                            isDark: true,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),

                  // Profession & Education
                  if (profile.profession.isNotEmpty || profile.education.isNotEmpty)
                    Text(
                      [
                        if (profile.profession.isNotEmpty) profile.profession,
                        if (profile.education.isNotEmpty) profile.education,
                      ].join(' • '),
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 13.5,
                        fontWeight: FontWeight.w500,
                        color: Colors.white.withValues(alpha: 0.90),
                      ),
                    ),
                  const SizedBox(height: 8),

                  // Bio Prose
                  if (profile.bio.isNotEmpty)
                    Text(
                      profile.bio,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 13,
                        height: 1.35,
                        color: Colors.white.withValues(alpha: 0.80),
                      ),
                    ),
                  const SizedBox(height: 12),

                  // 7-second Voice Spark play button
                  _buildVoiceSparkButton(profile, tokens),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
    );
  }

  Widget _buildPlaceholderPhoto(SanctuaryGlassTokens tokens) {
    return Container(
      color: const Color(0xFF1B1E24),
      child: Center(
        child: Icon(
          Icons.person_rounded,
          size: 96,
          color: Colors.white.withValues(alpha: 0.3),
        ),
      ),
    );
  }

  Widget _buildVoiceSparkButton(DiscoveryProfile profile, SanctuaryGlassTokens tokens) {
    final promptText = profile.voiceSparkPrompt ?? 'Voice Spark';
    return InkWell(
      onTap: _toggleVoiceSpark,
      borderRadius: BorderRadius.circular(20.0),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 8.0),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(20.0),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.3),
            width: 0.8,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _isPlayingVoiceSpark ? Icons.pause_rounded : Icons.play_arrow_rounded,
              size: 20,
              color: SanctuaryGlassTokens.brandSacredGold,
            ),
            const SizedBox(width: 8),
            Text(
              _isPlayingVoiceSpark
                  ? 'Playing Spark (${_voiceSparkProgress.toStringAsFixed(1)}s / 7.0s)'
                  : '$promptText (7s)',
              style: const TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionDeckControls(
    DiscoveryProfile profile,
    int swipesRemaining,
    bool isSwiping,
    SanctuaryGlassTokens tokens,
    bool isDark,
  ) {
    final canSwipe = swipesRemaining > 0 && !isSwiping;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          // 1. Pass with Grace Button (Left)
          _buildActionButton(
            icon: Icons.close_rounded,
            iconColor: tokens.textSecondary,
            tint: tokens.glassTintSecondary,
            size: 56.0,
            tooltip: 'Pass with Grace',
            onTap: canSwipe
                ? () {
                    _voiceSparkTimer?.cancel();
                    setState(() => _isPlayingVoiceSpark = false);
                    ref
                        .read(feedControllerProvider.notifier)
                        .handleSwipe(profile.id, 'pass');
                  }
                : null,
          ),

          // 2. Direct Letter Button (Center)
          _buildActionButton(
            icon: Icons.mark_email_read_outlined,
            iconColor: SanctuaryGlassTokens.brandSacredGold,
            tint: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
            size: 50.0,
            tooltip: 'Direct Letter',
            onTap: canSwipe
                ? () => _showDirectLetterDialog(context, profile, tokens, isDark)
                : null,
          ),

          // 3. Resonate Button (Right)
          _buildActionButton(
            icon: Icons.favorite_rounded,
            iconColor: Colors.white,
            tint: SanctuaryGlassTokens.brandTerracotta,
            size: 64.0,
            tooltip: 'Resonate',
            onTap: canSwipe
                ? () {
                    _voiceSparkTimer?.cancel();
                    setState(() => _isPlayingVoiceSpark = false);
                    ref
                        .read(feedControllerProvider.notifier)
                        .handleSwipe(profile.id, 'like');
                  }
                : null,
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required Color iconColor,
    required Color tint,
    required double size,
    required String tooltip,
    required VoidCallback? onTap,
  }) {
    return Tooltip(
      message: tooltip,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: tint,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.20),
              offset: const Offset(0, 6),
              blurRadius: 16.0,
            ),
          ],
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.35),
            width: 1.2,
          ),
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            customBorder: const CircleBorder(),
            child: Center(
              child: Icon(
                icon,
                color: onTap != null ? iconColor : iconColor.withValues(alpha: 0.4),
                size: size * 0.45,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DirectLetterDialog extends StatefulWidget {
  final DiscoveryProfile profile;
  final SanctuaryGlassTokens tokens;
  final bool isDark;
  final void Function(String text) onSend;

  const _DirectLetterDialog({
    required this.profile,
    required this.tokens,
    required this.isDark,
    required this.onSend,
  });

  @override
  State<_DirectLetterDialog> createState() => _DirectLetterDialogState();
}

class _DirectLetterDialogState extends State<_DirectLetterDialog> {
  late final TextEditingController _textController;

  @override
  void initState() {
    super.initState();
    _textController = TextEditingController();
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final charCount = _textController.text.length;
    final isOverLimit = charCount > 280;

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 24.0),
      child: SanctuaryGlassContainer(
        borderRadius: 20.0,
        blurSigma: 16.0,
        padding: const EdgeInsets.all(20.0),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.mark_email_read_outlined,
                    color: SanctuaryGlassTokens.brandSacredGold,
                    size: 24,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Direct Letter with Grace',
                      style: SanctuaryTypography.titleH2(
                        widget.tokens.textPrimary,
                        isDark: widget.isDark,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                'Compose a thoughtful note to ${widget.profile.fullName}. Direct letters accompany your resonance.',
                style: TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  fontSize: 13,
                  color: widget.tokens.textSecondary,
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _textController,
                maxLines: 4,
                maxLength: 280,
                onChanged: (_) => setState(() {}),
                style: TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  fontSize: 14,
                  color: widget.tokens.textPrimary,
                ),
                decoration: InputDecoration(
                  hintText: 'Share what resonated in their prose...',
                  hintStyle: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    color: widget.tokens.textTertiary,
                  ),
                  filled: true,
                  fillColor: widget.tokens.glassTintPrimary,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12.0),
                    borderSide: BorderSide(
                      color: widget.tokens.borderSpecularStart,
                    ),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12.0),
                    borderSide: BorderSide(
                      color: widget.tokens.borderSpecularStart.withValues(alpha: 0.5),
                    ),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12.0),
                    borderSide: const BorderSide(
                      color: SanctuaryGlassTokens.brandSacredGold,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: Text(
                      'Cancel',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        color: widget.tokens.textSecondary,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: SanctuaryGlassTokens.brandSacredGold,
                      foregroundColor: Colors.black,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12.0),
                      ),
                    ),
                    onPressed: (charCount == 0 || isOverLimit)
                        ? null
                        : () {
                            final note = _textController.text;
                            Navigator.of(context).pop();
                            widget.onSend(note);
                          },
                    child: const Text('Send & Resonate'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

