import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';
import '../../../feed/domain/models/discovery_profile.dart';

const Object _unset = Object();

@immutable
class SeekerProfileState {
  final DiscoveryProfile? profile;
  final bool isPhotoVeiled;
  final String revealStatus; // 'veiled', 'pending', 'accepted', 'purchased_unlock', 'declined'
  final bool isLoading;
  final bool isProcessingAction;
  final String? errorMessage;

  const SeekerProfileState({
    this.profile,
    this.isPhotoVeiled = true,
    this.revealStatus = 'veiled',
    this.isLoading = false,
    this.isProcessingAction = false,
    this.errorMessage,
  });

  SeekerProfileState copyWith({
    DiscoveryProfile? profile,
    bool? isPhotoVeiled,
    String? revealStatus,
    bool? isLoading,
    bool? isProcessingAction,
    Object? errorMessage = _unset,
  }) {
    return SeekerProfileState(
      profile: profile ?? this.profile,
      isPhotoVeiled: isPhotoVeiled ?? this.isPhotoVeiled,
      revealStatus: revealStatus ?? this.revealStatus,
      isLoading: isLoading ?? this.isLoading,
      isProcessingAction: isProcessingAction ?? this.isProcessingAction,
      errorMessage: errorMessage == _unset
          ? this.errorMessage
          : errorMessage as String?,
    );
  }
}

class SeekerProfileController extends StateNotifier<SeekerProfileState> {
  final SanctuaryHttpClient _client;
  final String _userId;

  SeekerProfileController(
    this._client,
    this._userId, [
    DiscoveryProfile? initialProfile,
  ]) : super(SeekerProfileState(
          profile: initialProfile,
          isPhotoVeiled: initialProfile?.isPhotoVeiled ?? true,
        )) {
    loadProfile(_userId, initial: initialProfile);
  }

  Future<void> loadProfile(String userId, {DiscoveryProfile? initial}) async {
    state = state.copyWith(
      isLoading: state.profile == null && initial == null,
      errorMessage: null,
      profile: initial ?? state.profile,
    );

    try {
      // 1. Fetch photo veil unmask status
      final statusRes = await _client.get('/api/v1/revelation/photo/status/$userId');
      final statusData = statusRes['data'] is Map<String, dynamic>
          ? statusRes['data'] as Map<String, dynamic>
          : statusRes;

      final isRevealed = statusData['is_revealed'] as bool? ?? false;
      final status = statusData['status'] as String? ?? 'veiled';

      DiscoveryProfile? resolvedProfile = state.profile;

      // 2. Fetch public profile if not yet populated
      if (resolvedProfile == null) {
        try {
          final profileRes = await _client.get('/api/v1/revelation/profile/$userId');
          final profileData = profileRes['data'] is Map<String, dynamic>
              ? profileRes['data'] as Map<String, dynamic>
              : profileRes;
          if (profileData.isNotEmpty &&
              (profileData['id'] != null || profileData['full_name'] != null)) {
            resolvedProfile = DiscoveryProfile.fromJson(profileData);
          }
        } catch (_) {
          // If profile endpoint is unavailable, keep existing or minimal fallback
        }
      }

      if (resolvedProfile != null &&
          resolvedProfile.photos.isEmpty &&
          (initial?.photos.isNotEmpty ?? false)) {
        resolvedProfile = resolvedProfile.copyWith(
          photos: initial!.photos,
          avatarUrl: initial.avatarUrl,
        );
      }

      state = state.copyWith(
        profile: resolvedProfile,
        isPhotoVeiled: !isRevealed,
        revealStatus: status,
        isLoading: false,
      );
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.message,
      );
    } catch (_) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Unable to load profile veil status. Please verify connection.',
      );
    }
  }

  void setProfile(DiscoveryProfile profile) {
    state = state.copyWith(
      profile: profile,
      isPhotoVeiled: state.revealStatus == 'veiled' ? profile.isPhotoVeiled : state.isPhotoVeiled,
    );
  }

  Future<bool> requestPhotoReveal() async {
    if (state.isProcessingAction) return false;

    state = state.copyWith(isProcessingAction: true, errorMessage: null);

    try {
      final response = await _client.post(
        '/api/v1/revelation/photo/request',
        body: {'target_id': _userId},
      );

      final data = response['data'] is Map<String, dynamic>
          ? response['data'] as Map<String, dynamic>
          : response;

      final isRevealed = data['is_revealed'] as bool? ?? false;
      final status = data['status'] as String? ?? 'pending';

      state = state.copyWith(
        isPhotoVeiled: !isRevealed,
        revealStatus: status,
        isProcessingAction: false,
      );
      return true;
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(
        isProcessingAction: false,
        errorMessage: e.message,
      );
      return false;
    } catch (_) {
      state = state.copyWith(
        isProcessingAction: false,
        errorMessage: 'Failed to dispatch photo reveal request.',
      );
      return false;
    }
  }

  Future<bool> unlockWithPerk() async {
    if (state.isProcessingAction) return false;

    state = state.copyWith(isProcessingAction: true, errorMessage: null);

    try {
      final response = await _client.post(
        '/api/v1/revelation/photo/unlock-perk',
        body: {'target_id': _userId},
      );

      final data = response['data'] is Map<String, dynamic>
          ? response['data'] as Map<String, dynamic>
          : response;

      final isRevealed = data['is_revealed'] as bool? ?? true;
      final status = data['status'] as String? ?? 'purchased_unlock';

      state = state.copyWith(
        isPhotoVeiled: !isRevealed,
        revealStatus: status,
        isProcessingAction: false,
      );
      return true;
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(
        isProcessingAction: false,
        errorMessage: e.message,
      );
      return false;
    } catch (_) {
      state = state.copyWith(
        isProcessingAction: false,
        errorMessage: 'Instant Unveil micro-perk checkout failed.',
      );
      return false;
    }
  }

  void clearError() {
    state = state.copyWith(errorMessage: null);
  }
}

final seekerProfileControllerProvider = StateNotifierProvider.autoDispose
    .family<SeekerProfileController, SeekerProfileState, String>((ref, userId) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return SeekerProfileController(client, userId);
});
