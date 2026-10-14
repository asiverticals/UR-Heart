import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';

@immutable
class ResonancesState {
  final List<dynamic> incomingLikes;
  final List<dynamic> mutualMatches;
  final bool isLoading;
  final String? error;

  const ResonancesState({
    this.incomingLikes = const [],
    this.mutualMatches = const [],
    this.isLoading = false,
    this.error,
  });

  ResonancesState copyWith({
    List<dynamic>? incomingLikes,
    List<dynamic>? mutualMatches,
    bool? isLoading,
    String? error,
  }) {
    return ResonancesState(
      incomingLikes: incomingLikes ?? this.incomingLikes,
      mutualMatches: mutualMatches ?? this.mutualMatches,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class ResonancesController extends StateNotifier<ResonancesState> {
  final SanctuaryHttpClient _client;

  ResonancesController(this._client) : super(const ResonancesState()) {
    fetchResonances();
  }

  Future<void> fetchResonances() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final incoming = await _client.get('/api/v1/resonances/incoming');
      final mutual = await _client.get('/api/v1/resonances/mutual');
      final incomingList = incoming['data'] is List ? (incoming['data'] as List) : const [];
      final mutualList = mutual['data'] is List ? (mutual['data'] as List) : const [];
      if (!mounted) return;
      state = state.copyWith(
        incomingLikes: incomingList,
        mutualMatches: mutualList,
        isLoading: false,
      );
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

final resonancesControllerProvider =
    StateNotifierProvider<ResonancesController, ResonancesState>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return ResonancesController(client);
});
