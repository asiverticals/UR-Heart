import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../network/sanctuary_http_client.dart';

final sanctuaryBillingServiceProvider =
    Provider<SanctuaryBillingService>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return SanctuaryBillingService(client);
});

class SanctuaryBillingService {
  final SanctuaryHttpClient _client;

  SanctuaryBillingService(this._client);

  Future<Map<String, dynamic>> claimReward({
    required String transactionId,
    required String adType,
    required String network,
  }) async {
    return _client.post(
      '/api/v1/ads/claim-reward',
      body: {
        'transaction_id': transactionId,
        'ad_type': adType,
        'network': network,
      },
    );
  }
}
