import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';

enum AdNetwork {
  admob,
  meta,
  unity,
  liftoff,
  chartboost,
}

class AdWaterfallResult {
  final bool success;
  final AdNetwork? network;
  final String? transactionId;
  final String? errorMessage;
  final bool coolingActive;
  final int secondsUntilNextAd;

  const AdWaterfallResult.success({
    required this.network,
    required this.transactionId,
  })  : success = true,
        errorMessage = null,
        coolingActive = false,
        secondsUntilNextAd = 0;

  const AdWaterfallResult.coolingActive({
    required this.secondsUntilNextAd,
  })  : success = false,
        network = null,
        transactionId = null,
        coolingActive = true,
        errorMessage = 'Anti-bot cooling active. Please wait $secondsUntilNextAd seconds.';

  const AdWaterfallResult.failure({
    required this.errorMessage,
    this.coolingActive = false,
    this.secondsUntilNextAd = 0,
  })  : success = false,
        network = null,
        transactionId = null;
}

final adWaterfallServiceProvider = Provider<AdWaterfallService>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return AdWaterfallService(client);
});

class AdWaterfallService {
  final SanctuaryHttpClient _client;

  AdWaterfallService(this._client);

  /// Checks anti-bot cooling and daily ceiling status from backend sentinel.
  Future<Map<String, dynamic>> checkAdStatus() async {
    try {
      final res = await _client.get('/api/v1/ads/status');
      return (res['data'] as Map<String, dynamic>?) ?? res;
    } catch (e) {
      return {
        'cooling_active': false,
        'seconds_until_next_ad': 0,
        'daily_ads_watched': 0,
        'daily_ads_limit': 20,
      };
    }
  }

  /// Cascades through the 5-network waterfall: AdMob -> Meta -> Unity -> Liftoff -> Chartboost.
  Future<AdWaterfallResult> showRewardedAdWaterfall({
    required String currentUserId,
    required String adType,
  }) async {
    // 1. Check anti-bot cooling and daily velocity caps
    final status = await checkAdStatus();
    final coolingActive = status['cooling_active'] == true;
    final secondsUntilNext = (status['seconds_until_next_ad'] as num?)?.toInt() ?? 0;

    if (coolingActive && secondsUntilNext > 0) {
      return AdWaterfallResult.coolingActive(secondsUntilNextAd: secondsUntilNext);
    }

    final customData = jsonEncode({
      'user_id': currentUserId,
      'ad_type': adType,
      'timestamp': DateTime.now().millisecondsSinceEpoch,
    });

    final waterfall = [
      AdNetwork.admob,
      AdNetwork.meta,
      AdNetwork.unity,
      AdNetwork.liftoff,
      AdNetwork.chartboost,
    ];

    // 2. Cascade down the mediation waterfall
    for (final network in waterfall) {
      try {
        final res = await _dispatchNetworkAd(network, customData: customData);
        if (res.success) {
          return res;
        }
      } catch (e) {
        debugPrint('Waterfall fallback from ${network.name}: $e');
        continue;
      }
    }

    return const AdWaterfallResult.failure(
      errorMessage: 'All ad networks temporarily filled or unavailable. Please try again shortly.',
    );
  }

  Future<AdWaterfallResult> _dispatchNetworkAd(
    AdNetwork network, {
    required String customData,
  }) async {
    // shortcut: simulation bridge on debug/test runtime; in release mode, fallback until native SDK binaries wired
    if (kDebugMode) {
      final simulatedTxId = 'tx_${network.name}_${DateTime.now().millisecondsSinceEpoch}';
      return AdWaterfallResult.success(
        network: network,
        transactionId: simulatedTxId,
      );
    }
    return AdWaterfallResult.failure(
      errorMessage: '${network.name} SDK dispatch unavailable in release runtime without native integration',
    );
  }
}
