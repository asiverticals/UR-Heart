import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/billing/sanctuary_billing_service.dart';

@immutable
class GrowthHubState {
  final int rewardBalance;
  final int streakCount;
  final double restMultiplier;
  final bool isNightSlumberActive;
  final bool isLoading;
  final String? errorMessage;

  const GrowthHubState({
    required this.rewardBalance,
    required this.streakCount,
    required this.restMultiplier,
    required this.isNightSlumberActive,
    this.isLoading = false,
    this.errorMessage,
  });

  GrowthHubState copyWith({
    int? rewardBalance,
    int? streakCount,
    double? restMultiplier,
    bool? isNightSlumberActive,
    bool? isLoading,
    String? errorMessage,
  }) {
    return GrowthHubState(
      rewardBalance: rewardBalance ?? this.rewardBalance,
      streakCount: streakCount ?? this.streakCount,
      restMultiplier: restMultiplier ?? this.restMultiplier,
      isNightSlumberActive: isNightSlumberActive ?? this.isNightSlumberActive,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
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
