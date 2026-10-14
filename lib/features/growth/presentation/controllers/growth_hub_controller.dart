import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/billing/sanctuary_billing_service.dart';
import '../../data/store_catalog_model.dart';

@immutable
class GrowthHubState {
  final int rewardBalance;
  final int streakCount;
  final double restMultiplier;
  final bool isNightSlumberActive;
  final bool isLoading;
  final String? errorMessage;
  final List<StoreProduct> products;
  final int directLettersCount;
  final int boostPoints;
  final int swipesRemaining;
  final String subscriptionTier;
  final bool isAdFree;
  final int streakRemainingSeconds;

  const GrowthHubState({
    required this.rewardBalance,
    required this.streakCount,
    required this.restMultiplier,
    required this.isNightSlumberActive,
    this.isLoading = false,
    this.errorMessage,
    this.products = const [],
    this.directLettersCount = 1,
    this.boostPoints = 0,
    this.swipesRemaining = 25,
    this.subscriptionTier = 'free',
    this.isAdFree = false,
    this.streakRemainingSeconds = 86400,
  });

  GrowthHubState copyWith({
    int? rewardBalance,
    int? streakCount,
    double? restMultiplier,
    bool? isNightSlumberActive,
    bool? isLoading,
    String? errorMessage,
    List<StoreProduct>? products,
    int? directLettersCount,
    int? boostPoints,
    int? swipesRemaining,
    String? subscriptionTier,
    bool? isAdFree,
    int? streakRemainingSeconds,
  }) {
    return GrowthHubState(
      rewardBalance: rewardBalance ?? this.rewardBalance,
      streakCount: streakCount ?? this.streakCount,
      restMultiplier: restMultiplier ?? this.restMultiplier,
      isNightSlumberActive: isNightSlumberActive ?? this.isNightSlumberActive,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      products: products ?? this.products,
      directLettersCount: directLettersCount ?? this.directLettersCount,
      boostPoints: boostPoints ?? this.boostPoints,
      swipesRemaining: swipesRemaining ?? this.swipesRemaining,
      subscriptionTier: subscriptionTier ?? this.subscriptionTier,
      isAdFree: isAdFree ?? this.isAdFree,
      streakRemainingSeconds: streakRemainingSeconds ?? this.streakRemainingSeconds,
    );
  }
}

class GrowthHubController extends StateNotifier<GrowthHubState> {
  final SanctuaryBillingService _billingService;

  GrowthHubController(this._billingService)
      : super(const GrowthHubState(
          rewardBalance: 0,
          streakCount: 0,
          restMultiplier: 1.0,
          isNightSlumberActive: false,
        ));

  Future<void> fetchStoreCatalog() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final catalogRes = await _billingService.fetchStoreCatalog();
      final balancesRes = await _billingService.fetchBalances();

      final catalogData = catalogRes['data'] as Map<String, dynamic>? ?? catalogRes;
      final rawProducts = catalogData['products'] as List? ?? [];
      final products = rawProducts
          .map((p) => StoreProduct.fromJson(Map<String, dynamic>.from(p as Map)))
          .toList();

      final balancesData = balancesRes['data'] as Map<String, dynamic>? ?? balancesRes;

      if (!mounted) return;
      state = state.copyWith(
        products: products,
        rewardBalance: (balancesData['reward_balance'] as num?)?.toInt() ?? state.rewardBalance,
        streakCount: (balancesData['streak_count'] as num?)?.toInt() ?? state.streakCount,
        directLettersCount: (balancesData['direct_letters_count'] as num?)?.toInt() ?? state.directLettersCount,
        boostPoints: (balancesData['boost_points'] as num?)?.toInt() ?? state.boostPoints,
        swipesRemaining: (balancesData['swipes_remaining'] as num?)?.toInt() ?? state.swipesRemaining,
        subscriptionTier: (balancesData['subscription_tier'] as String?) ?? state.subscriptionTier,
        isAdFree: (balancesData['is_ad_free'] as bool?) ?? state.isAdFree,
        isLoading: false,
      );
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  Future<void> claimAdReward({
    required String transactionId,
    required String adType,
    required String network,
  }) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final result = await _billingService.claimReward(
        transactionId: transactionId,
        adType: adType,
        network: network,
      );
      final dynamic balanceVal = result['new_balance'] ??
          (result['data'] is Map ? (result['data'] as Map)['new_balance'] : null);
      final newBalance =
          balanceVal is num ? balanceVal.toInt() : state.rewardBalance;
      if (!mounted) return;
      state = state.copyWith(
        rewardBalance: newBalance,
        isLoading: false,
      );
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  void updateSlumberMultiplier(double multiplier) {
    state = state.copyWith(
      restMultiplier: multiplier,
      isNightSlumberActive: multiplier > 1.0,
    );
  }
}

final growthHubControllerProvider =
    StateNotifierProvider<GrowthHubController, GrowthHubState>((ref) {
  final billingService = ref.watch(sanctuaryBillingServiceProvider);
  return GrowthHubController(billingService);
});
