import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';

@immutable
class BlindDateState {
  final bool isMilestoneLocked;
  final int currentMau;
  final int targetMau;
  final String queueStatus; // 'idle', 'waiting', 'paired'
  final String? activeSessionId;
  final int remainingSeconds;
  final bool isLoading;

  const BlindDateState({
    this.isMilestoneLocked = true,
    this.currentMau = 0,
    this.targetMau = 1000000,
    this.queueStatus = 'idle',
    this.activeSessionId,
    this.remainingSeconds = 180,
    this.isLoading = false,
  });

  BlindDateState copyWith({
    bool? isMilestoneLocked,
    int? currentMau,
    int? targetMau,
    String? queueStatus,
    String? activeSessionId,
    int? remainingSeconds,
    bool? isLoading,
  }) {
    return BlindDateState(
      isMilestoneLocked: isMilestoneLocked ?? this.isMilestoneLocked,
      currentMau: currentMau ?? this.currentMau,
      targetMau: targetMau ?? this.targetMau,
      queueStatus: queueStatus ?? this.queueStatus,
      activeSessionId: activeSessionId ?? this.activeSessionId,
      remainingSeconds: remainingSeconds ?? this.remainingSeconds,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class BlindDateController extends StateNotifier<BlindDateState> {
  final SanctuaryHttpClient _client;

  BlindDateController(this._client) : super(const BlindDateState()) {
    checkMilestoneStatus();
  }

  Future<void> checkMilestoneStatus() async {
    try {
      final res = await _client.get('/api/v1/blind-date/eligibility');
      final data = res['data'] is Map ? (res['data'] as Map<String, dynamic>) : res;
      final status = data['status'];
      final currentMau = data['current_mau'];
      final targetMau = data['target_mau'];
      if (!mounted) return;
      state = state.copyWith(
        isMilestoneLocked: status == 'milestone_locked',
        currentMau: currentMau is int ? currentMau : (currentMau is num ? currentMau.toInt() : 0),
        targetMau: targetMau is int ? targetMau : (targetMau is num ? targetMau.toInt() : 1000000),
      );
    } catch (_) {}
  }

  Future<void> joinQueue() async {
    state = state.copyWith(isLoading: true);
    try {
      await _client.post('/api/v1/blind-date/queue/join', body: {});
      if (!mounted) return;
      state = state.copyWith(
        queueStatus: 'waiting',
        isLoading: false,
      );
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false);
    }
  }
}

final blindDateControllerProvider =
    StateNotifierProvider<BlindDateController, BlindDateState>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return BlindDateController(client);
});
