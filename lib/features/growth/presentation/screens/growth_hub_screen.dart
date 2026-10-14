import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../../data/store_catalog_model.dart';
import '../controllers/growth_hub_controller.dart';
import '../widgets/morning_harvest_dialog.dart';
import '../widgets/streak_gauge_widget.dart';

/// Screen 7: GrowthHubScreen (/growth / Tab 3 in SanctuaryNavigationShell)
/// Hosts Mindful Streak, Accelerometer Slumber Harvest, 4 Rewarded Ad triggers,
/// and the Condition C2-gated Sovereign Micro-Perk & Pass Catalog.
class GrowthHubScreen extends ConsumerStatefulWidget {
  final void Function(StoreProduct product)? onProductTap;
  final VoidCallback? onAdHarvestTap;

  const GrowthHubScreen({
    super.key,
    this.onProductTap,
    this.onAdHarvestTap,
  });

  @override
  ConsumerState<GrowthHubScreen> createState() => _GrowthHubScreenState();
}

class _GrowthHubScreenState extends ConsumerState<GrowthHubScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(growthHubControllerProvider.notifier).fetchStoreCatalog();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(growthHubControllerProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: SafeArea(
        child: RefreshIndicator(
          color: SanctuaryGlassTokens.brandSacredGold,
          onRefresh: () async {
            await ref.read(growthHubControllerProvider.notifier).fetchStoreCatalog();
          },
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(
              parent: BouncingScrollPhysics(),
            ),
            slivers: [
              // Top Frosted Glass Header with Seeker Wallet Balances Pill
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              'Growth Hub & Store',
                              style: TextStyle(
                                fontFamily: SanctuaryTypography.serifFont,
                                fontSize: 22.0,
                                color: tokens.textPrimary,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          _buildBalancesPill(state, tokens),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Restorative habits, mindful rhythm & sovereign perks',
                        style: SanctuaryTypography.bodySmall(tokens.textSecondary),
                      ),
                    ],
                  ),
                ),
              ),

              // Section 1: Mindful Rhythm & Rest
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSectionHeader('Mindful Rhythm & Rest', tokens),
                      const SizedBox(height: 12),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // 24h Streak Gauge
                          Expanded(
                            flex: 5,
                            child: Center(
                              child: StreakGaugeWidget(
                                streakCount: state.streakCount,
                                remainingSeconds: state.streakRemainingSeconds,
                                size: 160.0,
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          // Accelerometer Night Slumber Card
                          Expanded(
                            flex: 6,
                            child: _buildSlumberCard(state, tokens),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),

              // Section 2: Mindful Ad Reflection Triggers (4 Frosted Cards)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSectionHeader('Mindful Ad Reflection Rituals', tokens),
                      const SizedBox(height: 12),
                      _buildAdTriggersGrid(state, tokens),
                    ],
                  ),
                ),
              ),

              // Section 3: Sovereign Micro-Perks Grid
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16.0, 24.0, 16.0, 8.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildSectionHeader('Sovereign Micro-Perks', tokens),
                      const SizedBox(height: 4),
                      Text(
                        'Intentional unlocks without recurring subscriptions.',
                        style: SanctuaryTypography.bodySmall(tokens.textSecondary),
                      ),
                      const SizedBox(height: 12),
                      _buildMicroPerksGrid(state, tokens),
                    ],
                  ),
                ),
              ),

              // Section 4: Sovereign Passes Banner
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: _buildSovereignPassesBanner(state, tokens),
                ),
              ),

              const SliverToBoxAdapter(child: SizedBox(height: 80)),
            ],
          ),
        ),
      ),
    );
  }

  // --- Sub-Components ---

  Widget _buildBalancesPill(GrowthHubState state, SanctuaryGlassTokens tokens) {
    return SanctuaryGlassContainer(
      borderRadius: 24,
      blurSigma: 12,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.stars, color: SanctuaryGlassTokens.brandSacredGold, size: 16),
          const SizedBox(width: 4),
          Text(
            '${state.rewardBalance}',
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              color: tokens.textPrimary,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
          const SizedBox(width: 10),
          const Icon(Icons.mail_outline, color: SanctuaryGlassTokens.brandTerracotta, size: 16),
          const SizedBox(width: 4),
          Text(
            '${state.directLettersCount}',
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              color: tokens.textPrimary,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
          const SizedBox(width: 10),
          const Icon(Icons.bolt, color: SanctuaryGlassTokens.brandSacredGold, size: 16),
          const SizedBox(width: 4),
          Text(
            '${state.swipesRemaining}',
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              color: tokens.textPrimary,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title, SanctuaryGlassTokens tokens) {
    return Text(
      title,
      style: TextStyle(
        fontFamily: SanctuaryTypography.serifFont,
        color: tokens.textPrimary,
        fontWeight: FontWeight.w700,
        fontSize: 17,
        letterSpacing: 0.2,
      ),
    );
  }

  Widget _buildSlumberCard(GrowthHubState state, SanctuaryGlassTokens tokens) {
    final multiplierText = '${state.restMultiplier.toStringAsFixed(1)}x';
    return SanctuaryGlassContainer(
      borderRadius: 20,
      blurSigma: 14,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Icon(Icons.nights_stay, color: SanctuaryGlassTokens.brandSacredGold, size: 22),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.4),
                    width: 1,
                  ),
                ),
                child: Text(
                  multiplierText,
                  style: const TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    color: SanctuaryGlassTokens.brandSacredGold,
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            'Night Slumber',
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              color: tokens.textPrimary,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Rest yield active. Accelerometer tracks restorative stillness.',
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              color: tokens.textSecondary,
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 10),
          InkWell(
            onTap: () {
              MorningHarvestDialog.show(
                context,
                sleepHours: 8.0,
                onHarvestSuccess: () {
                  ref.read(growthHubControllerProvider.notifier).fetchStoreCatalog();
                },
              );
            },
            borderRadius: BorderRadius.circular(10),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 10),
              decoration: BoxDecoration(
                color: tokens.glassTintElevated,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: tokens.borderSpecularStart.withValues(alpha: 0.3),
                  width: 1,
                ),
              ),
              child: const Center(
                child: Text(
                  'Morning Harvest',
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    color: SanctuaryGlassTokens.brandSacredGold,
                    fontWeight: FontWeight.w600,
                    fontSize: 11,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAdTriggersGrid(GrowthHubState state, SanctuaryGlassTokens tokens) {
    final adTriggers = [
      {
        'title': 'Quick Reflection',
        'duration': '10s video',
        'reward': '+10 Swipes, +10 Boost',
        'icon': Icons.flash_on,
        'type': 'quick_reflection',
      },
      {
        'title': 'Deep Resonance',
        'duration': '20s video',
        'reward': '+1 Direct Letter, +25 Boost',
        'icon': Icons.self_improvement,
        'type': 'deep_resonance',
      },
      {
        'title': 'Sacred Bridge Reveal',
        'duration': '30s video',
        'reward': '+1/3 Contact Unseal',
        'icon': Icons.vpn_key,
        'type': 'sacred_bridge_reveal',
      },
      {
        'title': 'Harvest Boost',
        'duration': 'Scaled yield',
        'reward': '${state.restMultiplier.toStringAsFixed(1)}x Slumber Yield',
        'icon': Icons.eco,
        'type': 'morning_harvest_unlock',
      },
    ];

    return GridView.builder(
      physics: const NeverScrollableScrollPhysics(),
      shrinkWrap: true,
      itemCount: adTriggers.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
        mainAxisExtent: 105,
      ),
      itemBuilder: (context, index) {
        final item = adTriggers[index];
        return InkWell(
          onTap: () {
            widget.onAdHarvestTap?.call();
            ref.read(growthHubControllerProvider.notifier).claimAdReward(
                  transactionId: 'ad_tx_${DateTime.now().millisecondsSinceEpoch}',
                  adType: item['type'] as String,
                  network: 'admob',
                );
          },
          borderRadius: BorderRadius.circular(16),
          child: SanctuaryGlassContainer(
            borderRadius: 16,
            blurSigma: 12,
            padding: const EdgeInsets.all(10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Icon(item['icon'] as IconData, color: SanctuaryGlassTokens.brandSacredGold, size: 18),
                    const SizedBox(width: 4),
                    Flexible(
                      child: Text(
                        item['duration'] as String,
                        style: TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          color: tokens.textSecondary,
                          fontSize: 10,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                Text(
                  item['title'] as String,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    color: tokens.textPrimary,
                    fontWeight: FontWeight.w600,
                    fontSize: 12.5,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  item['reward'] as String,
                  style: const TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    color: SanctuaryGlassTokens.brandTerracotta,
                    fontSize: 10.5,
                    fontWeight: FontWeight.bold,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildMicroPerksGrid(GrowthHubState state, SanctuaryGlassTokens tokens) {
    // Fallback static list if store catalog is still loading
    final microPerks = state.products.where((p) => p.productClass == 'micro_perk').toList();
    final items = microPerks.isNotEmpty
        ? microPerks
        : [
            const StoreProduct(
              id: 'direct_letter_single',
              title: 'Direct Thought Letter',
              description: 'Bypasses discovery deck to create dialogue.',
              productClass: 'micro_perk',
              inrPrice: 29.0,
              currencySymbol: '₹',
              badgeLabel: 'Popular',
            ),
            const StoreProduct(
              id: 'profile_unlock_single',
              title: 'Modesty Veil Unveil',
              description: 'Unveils 35px photo blur veil for a single seeker.',
              productClass: 'micro_perk',
              inrPrice: 39.0,
              currencySymbol: '₹',
            ),
            const StoreProduct(
              id: 'super_like_pack_3',
              title: 'Resonance Spark (x3)',
              description: '+3 High-resonance Super Likes with top deck placement.',
              productClass: 'micro_perk',
              inrPrice: 49.0,
              currencySymbol: '₹',
              badgeLabel: '3x Spark',
            ),
            const StoreProduct(
              id: 'spotlight_boost_24h',
              title: '24h Sanctuary Spotlight',
              description: '24-hour priority discovery placement (+100 Boost Points).',
              productClass: 'micro_perk',
              inrPrice: 79.0,
              currencySymbol: '₹',
              badgeLabel: '24 Hours',
            ),
            const StoreProduct(
              id: 'sacred_bridge_instant',
              title: 'Instant Bridge Key',
              description: 'Instant reveal of contact without 3-ad ritual.',
              productClass: 'micro_perk',
              inrPrice: 99.0,
              currencySymbol: '₹',
              badgeLabel: 'Instant',
            ),
          ];

    return GridView.builder(
      physics: const NeverScrollableScrollPhysics(),
      shrinkWrap: true,
      itemCount: items.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
        mainAxisExtent: 175,
      ),
      itemBuilder: (context, index) {
        final product = items[index];
        return SanctuaryGlassContainer(
          borderRadius: 18,
          blurSigma: 14,
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (product.badgeLabel != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  margin: const EdgeInsets.only(bottom: 6),
                  decoration: BoxDecoration(
                    color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.4),
                      width: 1,
                    ),
                  ),
                  child: Text(
                    product.badgeLabel!,
                    style: const TextStyle(
                      fontFamily: SanctuaryTypography.sansFont,
                      color: SanctuaryGlassTokens.brandSacredGold,
                      fontSize: 9.5,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              Text(
                product.title,
                style: TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  color: tokens.textPrimary,
                  fontWeight: FontWeight.w600,
                  fontSize: 12.5,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              Expanded(
                child: Text(
                  product.description,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    color: tokens.textSecondary,
                    fontSize: 10.5,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(height: 8),
              InkWell(
                onTap: () {
                  widget.onProductTap?.call(product);
                },
                borderRadius: BorderRadius.circular(10),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 7),
                  decoration: BoxDecoration(
                    color: tokens.glassTintElevated,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.6),
                      width: 1,
                    ),
                  ),
                  child: Center(
                    child: Text(
                      product.formattedPrice,
                      style: const TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        color: SanctuaryGlassTokens.brandSacredGold,
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSovereignPassesBanner(GrowthHubState state, SanctuaryGlassTokens tokens) {
    final passes = state.products.where((p) => p.isPass).toList();
    final items = passes.isNotEmpty
        ? passes
        : [
            const StoreProduct(
              id: 'pass_sovereign_weekly',
              title: 'Sovereign Pass (7 Days)',
              description: 'Unlimited Swipes, Ad-Free UI, +5 Direct Letters for 7 days.',
              productClass: 'pass',
              inrPrice: 299.0,
              currencySymbol: '₹',
              badgeLabel: '7 Days',
            ),
            const StoreProduct(
              id: 'pass_sovereign_monthly',
              title: 'Sovereign Pass (30 Days)',
              description: 'Complete Sanctuary access, +25 Letters, Voice Badge for 30 days.',
              productClass: 'pass',
              inrPrice: 999.0,
              currencySymbol: '₹',
              badgeLabel: 'Most Mindful',
            ),
            const StoreProduct(
              id: 'pass_sovereign_quarter',
              title: 'Sovereign Pass (90 Days)',
              description: 'Complete access + AI Wingman priority for 90 days.',
              productClass: 'pass',
              inrPrice: 2499.0,
              currencySymbol: '₹',
              badgeLabel: 'Best Value',
            ),
          ];

    return SanctuaryGlassContainer(
      borderRadius: 24,
      blurSigma: 20,
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.workspace_premium, color: SanctuaryGlassTokens.brandSacredGold, size: 26),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Sovereign Sanctuary Passes',
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.serifFont,
                    color: tokens.textPrimary,
                    fontWeight: FontWeight.w700,
                    fontSize: 17,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Unrestricted access for intentional connection. Fixed duration, never recurring.',
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              color: tokens.textSecondary,
              fontSize: 11.5,
            ),
          ),
          const SizedBox(height: 14),
          ...items.map((pass) => _buildPassItem(pass, tokens)),
          const SizedBox(height: 12),
          const Center(
            child: Text(
              'One-time mindful payment. Never auto-charged.',
              style: TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                color: SanctuaryGlassTokens.brandTerracotta,
                fontStyle: FontStyle.italic,
                fontWeight: FontWeight.w600,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPassItem(StoreProduct pass, SanctuaryGlassTokens tokens) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: tokens.glassTintElevated,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: tokens.borderSpecularStart.withValues(alpha: 0.35),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      pass.title,
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        color: tokens.textPrimary,
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                      ),
                    ),
                    if (pass.badgeLabel != null) ...[
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          pass.badgeLabel!,
                          style: const TextStyle(
                            fontFamily: SanctuaryTypography.sansFont,
                            color: SanctuaryGlassTokens.brandSacredGold,
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  pass.description,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    color: tokens.textSecondary,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          ElevatedButton(
            onPressed: () {
              widget.onProductTap?.call(pass);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: SanctuaryGlassTokens.brandSacredGold,
              foregroundColor: Colors.black,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            ),
            child: Text(
              pass.formattedPrice,
              style: const TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontWeight: FontWeight.bold,
                color: Colors.black,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
