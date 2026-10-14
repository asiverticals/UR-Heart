import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';

@immutable
class VaultState {
  final List<dynamic> grievances;
  final Map<String, dynamic>? nominee;
  final bool isExportPending;
  final bool isLoading;

  const VaultState({
    this.grievances = const [],
    this.nominee,
    this.isExportPending = false,
    this.isLoading = false,
  });

  VaultState copyWith({
    List<dynamic>? grievances,
    Map<String, dynamic>? nominee,
    bool clearNominee = false,
    bool? isExportPending,
    bool? isLoading,
  }) {
    return VaultState(
      grievances: grievances ?? this.grievances,
      nominee: clearNominee ? null : (nominee ?? this.nominee),
      isExportPending: isExportPending ?? this.isExportPending,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class VaultController extends StateNotifier<VaultState> {
  final SanctuaryHttpClient _client;

  VaultController(this._client) : super(const VaultState()) {
    loadVaultData();
  }

  Future<void> loadVaultData() async {
    state = state.copyWith(isLoading: true);
    try {
      final grv = await _client.get('/api/v1/vault/grievances');
      final nom = await _client.get('/api/v1/vault/nominee');
      final grvList = grv['data'] is List ? (grv['data'] as List) : const [];
      final dynamic rawNom = nom['data'];
      final nomData = rawNom is Map<String, dynamic> ? rawNom : null;
      if (!mounted) return;
      state = state.copyWith(
        grievances: grvList,
        nominee: nomData,
        clearNominee: nomData == null,
        isLoading: false,
      );
    } catch (_) {
      if (!mounted) return;
      state = state.copyWith(isLoading: false);
    }
  }
}

final vaultControllerProvider =
    StateNotifierProvider<VaultController, VaultState>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return VaultController(client);
});
