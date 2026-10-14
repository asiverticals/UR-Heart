import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';
import '../../domain/models/discovery_profile.dart';

const Object _unset = Object();

@immutable
class FeedState {
  final List<DiscoveryProfile> profiles;
  final int swipesRemaining;
  final bool isLoading;
  final bool isSwiping;
  final String? matchedId;
  final String? errorMessage;

  const FeedState({
    this.profiles = const [],
    this.swipesRemaining = 10,
    this.isLoading = false,
    this.isSwiping = false,
    this.matchedId,
    this.errorMessage,
  });

  FeedState copyWith({
    List<DiscoveryProfile>? profiles,
    int? swipesRemaining,
    bool? isLoading,
    bool? isSwiping,
    Object? matchedId = _unset,
    Object? errorMessage = _unset,
  }) {
    return FeedState(
      profiles: profiles ?? this.profiles,
      swipesRemaining: swipesRemaining ?? this.swipesRemaining,
      isLoading: isLoading ?? this.isLoading,
      isSwiping: isSwiping ?? this.isSwiping,
      matchedId: matchedId == _unset ? this.matchedId : matchedId as String?,
      errorMessage: errorMessage == _unset
          ? this.errorMessage
          : errorMessage as String?,
    );
  }
}

class FeedController extends StateNotifier<FeedState> {
  final SanctuaryHttpClient _client;

  FeedController(this._client) : super(const FeedState());

  Future<void> fetchDeck() async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final response = await _client.get('/api/v1/feed');
      final data = response['data'] is Map<String, dynamic>
          ? response['data'] as Map<String, dynamic>
          : response;

      final profilesRaw = (data['profiles'] as List<dynamic>?) ?? [];
      final profiles = profilesRaw
          .whereType<Map<String, dynamic>>()
          .map((p) => DiscoveryProfile.fromJson(p))
          .toList();

      final remaining = (data['swipes_remaining'] as num?)?.toInt() ?? 10;

      state = state.copyWith(
        profiles: profiles,
        swipesRemaining: remaining,
        isLoading: false,
        errorMessage: null,
      );
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.message,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Unable to load discovery deck. Please verify network.',
      );
    }
  }

  Future<bool> handleSwipe(
    String targetId,
    String action, {
    String? directLetter,
  }) async {
    if (state.isSwiping) {
      return false;
    }

    if (state.swipesRemaining <= 0) {
      state = state.copyWith(
        errorMessage:
            "You have met today's rhythm. Return tomorrow or complete a mindful reflection.",
      );
      return false;
    }

    // Optimistically remove the top card
    final previousProfiles = state.profiles;
    final updatedProfiles =
        state.profiles.where((p) => p.id != targetId).toList();

    state = state.copyWith(
      profiles: updatedProfiles,
      swipesRemaining: state.swipesRemaining - 1,
      isSwiping: true,
      errorMessage: null,
    );

    try {
      final body = <String, dynamic>{
        'target_id': targetId,
        'action': action,
      };
      if (directLetter != null && directLetter.trim().isNotEmpty) {
        body['direct_letter_text'] = directLetter.trim();
      }

      final response = await _client.post(
        '/api/v1/feed/swipe',
        body: body,
      );

      final data = response['data'] is Map<String, dynamic>
          ? response['data'] as Map<String, dynamic>
          : response;

      final isMatch = data['is_match'] as bool? ?? false;
      final matchId = data['match_id'] as String?;
      final remaining = (data['swipes_remaining'] as num?)?.toInt() ??
          state.swipesRemaining;

      state = state.copyWith(
        swipesRemaining: remaining,
        matchedId: isMatch ? matchId : null,
      );
      return true;
    } on SanctuaryClientException catch (e) {
      if (e.errorCode == 'DAILY_SWIPE_QUOTA_EXHAUSTED') {
        state = state.copyWith(
          profiles: previousProfiles,
          swipesRemaining: 0,
          errorMessage: e.message,
        );
      } else {
        // Rollback on unexpected failure (including non-quota 403s)
        state = state.copyWith(
          profiles: previousProfiles,
          swipesRemaining: state.swipesRemaining + 1,
          errorMessage: e.message,
        );
      }
      return false;
    } catch (_) {
      state = state.copyWith(
        profiles: previousProfiles,
        swipesRemaining: state.swipesRemaining + 1,
        errorMessage: 'Connection lost while sending your resonance.',
      );
      return false;
    } finally {
      state = state.copyWith(isSwiping: false);
    }
  }

  void clearMatch() {
    state = state.copyWith(matchedId: null);
  }

  void clearError() {
    state = state.copyWith(errorMessage: null);
  }
}

final feedControllerProvider =
    StateNotifierProvider<FeedController, FeedState>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return FeedController(client);
});
