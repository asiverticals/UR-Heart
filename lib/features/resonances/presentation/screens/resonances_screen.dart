import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../controllers/resonances_controller.dart';

/// Screen 1: ResonancesScreen (Main Bottom Nav Tab Index 1)
/// Displays incoming admirer deck and active mutual resonance connections.
class ResonancesScreen extends ConsumerStatefulWidget {
  const ResonancesScreen({super.key});

  @override
  ConsumerState<ResonancesScreen> createState() => _ResonancesScreenState();
}

class _ResonancesScreenState extends ConsumerState<ResonancesScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();
    final state = ref.watch(resonancesControllerProvider);

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Header
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Resonances',
                    style: SanctuaryTypography.titleH1(tokens.textPrimary, isDark: isDark),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Mutual harmonies & incoming vibrations',
                    style: SanctuaryTypography.caption(tokens.textSecondary),
                  ),
                ],
              ),
            ),

            // 2. Tab Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: SanctuaryGlassContainer(
                borderRadius: 24,
                padding: const EdgeInsets.all(4),
                child: TabBar(
                  controller: _tabController,
                  indicator: BoxDecoration(
                    color: tokens.glowTerracotta.withValues(alpha: 0.25),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: tokens.glowTerracotta.withValues(alpha: 0.5),
                      width: 1,
                    ),
                  ),
                  labelColor: tokens.textPrimary,
                  unselectedLabelColor: tokens.textSecondary,
                  labelStyle: const TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                  dividerColor: Colors.transparent,
                  tabs: [
                    Tab(
                      text: 'Mutual (${state.mutualMatches.length})',
                    ),
                    Tab(
                      text: 'Admirers (${state.incomingLikes.length})',
                    ),
                  ],
                ),
              ),
            ),

            // 3. Tab Views
            Expanded(
              child: state.isLoading
                  ? Center(
                      child: CircularProgressIndicator(
                        valueColor: AlwaysStoppedAnimation<Color>(tokens.glowTerracotta),
                      ),
                    )
                  : TabBarView(
                      controller: _tabController,
                      children: [
                        _buildMutualTab(state.mutualMatches, tokens, isDark),
                        _buildAdmirersTab(state.incomingLikes, tokens, isDark),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMutualTab(
    List<dynamic> mutualMatches,
    SanctuaryGlassTokens tokens,
    bool isDark,
  ) {
    if (mutualMatches.isEmpty) {
      return RefreshIndicator(
        onRefresh: () => ref.read(resonancesControllerProvider.notifier).fetchResonances(),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            const SizedBox(height: 100),
            Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40),
                child: Column(
                  children: [
                    Icon(Icons.favorite_border_rounded, size: 56, color: tokens.textSecondary),
                    const SizedBox(height: 16),
                    Text(
                      'No Mutual Resonances Yet',
                      style: SanctuaryTypography.titleH2(tokens.textPrimary, isDark: isDark),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Keep exploring the sanctuary deck. When hearts align, mutual resonance begins.',
                      textAlign: TextAlign.center,
                      style: SanctuaryTypography.bodyStandard(tokens.textSecondary),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(resonancesControllerProvider.notifier).fetchResonances(),
      child: ListView.separated(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
        itemCount: mutualMatches.length,
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          final item = Map<String, dynamic>.from(mutualMatches[index] as Map);
          final matchId = item['match_id']?.toString() ?? '';
          final peerId = item['peer_id']?.toString() ?? '';
          final peerName = item['peer_name']?.toString() ?? 'Seeker';
          final peerAvatar = item['peer_avatar']?.toString();

          return SanctuaryGlassContainer(
            borderRadius: 16,
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 28,
                  backgroundColor: tokens.glowTerracotta.withValues(alpha: 0.2),
                  backgroundImage: (peerAvatar != null && peerAvatar.isNotEmpty)
                      ? NetworkImage(peerAvatar)
                      : null,
                  child: (peerAvatar == null || peerAvatar.isEmpty)
                      ? Text(
                          peerName.isNotEmpty ? peerName[0].toUpperCase() : 'S',
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                            color: tokens.textPrimary,
                          ),
                        )
                      : null,
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        peerName,
                        style: TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          fontWeight: FontWeight.w600,
                          fontSize: 16,
                          color: tokens.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Mutual resonance established',
                        style: SanctuaryTypography.caption(tokens.textSecondary),
                      ),
                    ],
                  ),
                ),
                ElevatedButton(
                  onPressed: () {
                    context.push('/chat-dialogue?matchId=$matchId&peerId=$peerId');
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: tokens.glowTerracotta,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Text('Dialogue', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildAdmirersTab(
    List<dynamic> incomingLikes,
    SanctuaryGlassTokens tokens,
    bool isDark,
  ) {
    if (incomingLikes.isEmpty) {
      return RefreshIndicator(
        onRefresh: () => ref.read(resonancesControllerProvider.notifier).fetchResonances(),
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            const SizedBox(height: 100),
            Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40),
                child: Column(
                  children: [
                    Icon(Icons.visibility_off_outlined, size: 56, color: tokens.textSecondary),
                    const SizedBox(height: 16),
                    Text(
                      'No Incoming Admirers Yet',
                      style: SanctuaryTypography.titleH2(tokens.textPrimary, isDark: isDark),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'When another seeker resonates with your persona, their intent will be veiled here.',
                      textAlign: TextAlign.center,
                      style: SanctuaryTypography.bodyStandard(tokens.textSecondary),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(resonancesControllerProvider.notifier).fetchResonances(),
      child: ListView.separated(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
        itemCount: incomingLikes.length,
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          final item = Map<String, dynamic>.from(incomingLikes[index] as Map);
          final seekerId = item['seeker_id']?.toString() ?? '';
          final fullName = item['full_name']?.toString() ?? 'Secret Admirer';
          final bio = item['bio']?.toString() ?? '';
          final isSuperlike = item['is_superlike'] == true;
          final directLetter = item['direct_letter']?.toString();

          return SanctuaryGlassContainer(
            borderRadius: 16,
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      radius: 24,
                      backgroundColor: tokens.glowPine.withValues(alpha: 0.25),
                      child: Icon(Icons.lock_outline_rounded, size: 20, color: tokens.glowPine),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                fullName,
                                style: TextStyle(
                                  fontFamily: SanctuaryTypography.sansFont,
                                  fontWeight: FontWeight.w600,
                                  fontSize: 16,
                                  color: tokens.textPrimary,
                                ),
                              ),
                              if (isSuperlike) ...[
                                const SizedBox(width: 6),
                                Icon(Icons.star_rounded, size: 18, color: tokens.glowGold),
                              ],
                            ],
                          ),
                          const SizedBox(height: 2),
                          Text(
                            isSuperlike ? 'Sent a Super-Resonance' : 'Liked your persona',
                            style: SanctuaryTypography.caption(tokens.textSecondary),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                if (bio.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    bio,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: SanctuaryTypography.bodyStandard(tokens.textSecondary),
                  ),
                ],
                if (directLetter != null && directLetter.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: tokens.glowTerracotta.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: tokens.glowTerracotta.withValues(alpha: 0.25),
                      ),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.mail_outline_rounded, size: 16, color: tokens.glowTerracotta),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '"$directLetter"',
                            style: SanctuaryTypography.quote(tokens.textPrimary, isDark: isDark),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 14),
                Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    TextButton(
                      onPressed: () async {
                        final success = await ref
                            .read(resonancesControllerProvider.notifier)
                            .respondToSwipe(targetId: seekerId, swipeType: 'pass');
                        if (!success && context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Unable to process pass. Please try again.'),
                              duration: Duration(seconds: 2),
                            ),
                          );
                        }
                      },
                      child: Text(
                        'Pass with Grace',
                        style: TextStyle(color: tokens.textSecondary, fontSize: 13),
                      ),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton.icon(
                      onPressed: () async {
                        final success = await ref
                            .read(resonancesControllerProvider.notifier)
                            .respondToSwipe(targetId: seekerId, swipeType: 'like');
                        if (!success && context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Unable to resonate. Please try again.'),
                              duration: Duration(seconds: 2),
                            ),
                          );
                        }
                      },
                      icon: const Icon(Icons.favorite_rounded, size: 16),
                      label: const Text('Resonate', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: tokens.glowTerracotta,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
