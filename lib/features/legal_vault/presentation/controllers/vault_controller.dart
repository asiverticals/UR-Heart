import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';

@immutable
class NomineeModel {
  final String name;
  final String contact;
  final String relationship;
  final String? assignedAt;
  final String verificationStatus;

  const NomineeModel({
    required this.name,
    required this.contact,
    required this.relationship,
    this.assignedAt,
    this.verificationStatus = 'designated',
  });

  factory NomineeModel.fromJson(Map<String, dynamic> json) {
    return NomineeModel(
      name: json['nominee_name']?.toString() ?? json['full_name']?.toString() ?? json['name']?.toString() ?? '',
      contact: json['nominee_contact']?.toString() ?? json['phone']?.toString() ?? json['contact']?.toString() ?? '',
      relationship: json['relationship']?.toString() ?? '',
      assignedAt: json['assigned_at']?.toString(),
      verificationStatus: json['verification_status']?.toString() ?? 'designated',
    );
  }
}

@immutable
class GrievanceDossierModel {
  final String referenceId;
  final String category;
  final String evidence;
  final String status;
  final String acknowledgmentSentAt;
  final String statutoryResolutionDueAt;
  final String createdAt;

  const GrievanceDossierModel({
    required this.referenceId,
    required this.category,
    required this.evidence,
    required this.status,
    required this.acknowledgmentSentAt,
    required this.statutoryResolutionDueAt,
    required this.createdAt,
  });

  factory GrievanceDossierModel.fromJson(Map<String, dynamic> json) {
    return GrievanceDossierModel(
      referenceId: json['dossier_reference_id']?.toString() ?? json['id']?.toString() ?? '',
      category: json['violation_category']?.toString() ?? json['category']?.toString() ?? '',
      evidence: json['evidence_text']?.toString() ?? json['evidence']?.toString() ?? '',
      status: json['status']?.toString() ?? 'acknowledged',
      acknowledgmentSentAt: json['acknowledgment_sent_at']?.toString() ?? '',
      statutoryResolutionDueAt: json['statutory_resolution_due_at']?.toString() ?? '',
      createdAt: json['created_at']?.toString() ?? '',
    );
  }

  int get daysRemaining {
    try {
      final due = DateTime.parse(statutoryResolutionDueAt);
      final diff = due.difference(DateTime.now()).inDays;
      return diff < 0 ? 0 : diff;
    } catch (_) {
      return 15;
    }
  }
}

@immutable
class VaultState {
  final NomineeModel? nominee;
  final List<GrievanceDossierModel> grievances;
  final bool isExporting;
  final bool isLoading;
  final String? errorMessage;
  final String? successMessage;

  const VaultState({
    this.nominee,
    this.grievances = const [],
    this.isExporting = false,
    this.isLoading = false,
    this.errorMessage,
    this.successMessage,
  });

  VaultState copyWith({
    NomineeModel? nominee,
    bool clearNominee = false,
    List<GrievanceDossierModel>? grievances,
    bool? isExporting,
    bool? isLoading,
    String? errorMessage,
    String? successMessage,
    bool clearMessages = false,
  }) {
    return VaultState(
      nominee: clearNominee ? null : (nominee ?? this.nominee),
      grievances: grievances ?? this.grievances,
      isExporting: isExporting ?? this.isExporting,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: clearMessages ? null : (errorMessage ?? this.errorMessage),
      successMessage: clearMessages ? null : (successMessage ?? this.successMessage),
    );
  }
}

class VaultController extends StateNotifier<VaultState> {
  final SanctuaryHttpClient _client;

  VaultController(this._client) : super(const VaultState()) {
    loadVaultData();
  }

  Future<void> loadVaultData() async {
    state = state.copyWith(isLoading: true, clearMessages: true);
    try {
      final nomRes = await _client.get('/api/v1/legal/nominee');
      final grvRes = await _client.get('/api/v1/legal/grievances');

      NomineeModel? nominee;
      if (nomRes['data'] != null && nomRes['data'] is Map<String, dynamic>) {
        nominee = NomineeModel.fromJson(nomRes['data'] as Map<String, dynamic>);
      }

      final List<GrievanceDossierModel> grievances = [];
      if (grvRes['data'] != null && grvRes['data'] is List) {
        for (final item in grvRes['data'] as List) {
          if (item is Map<String, dynamic>) {
            grievances.add(GrievanceDossierModel.fromJson(item));
          }
        }
      }

      if (!mounted) return;
      state = state.copyWith(
        nominee: nominee,
        clearNominee: nominee == null,
        grievances: grievances,
        isLoading: false,
      );
    } catch (e) {
      if (!mounted) return;
      state = state.copyWith(
        isLoading: false,
        errorMessage: e.toString(),
      );
    }
  }

  Future<bool> saveNominee({
    required String name,
    required String contact,
    required String relationship,
  }) async {
    state = state.copyWith(isLoading: true, clearMessages: true);
    try {
      final res = await _client.post(
        '/api/v1/legal/nominee',
        body: {
          'nominee_name': name,
          'nominee_contact': contact,
          'relationship': relationship,
        },
      );
      if (res['data'] != null && res['data'] is Map<String, dynamic>) {
        final updated = NomineeModel.fromJson(res['data'] as Map<String, dynamic>);
        if (!mounted) return true;
        state = state.copyWith(
          nominee: updated,
          isLoading: false,
          successMessage: 'Digital nominee designated under Section 14.',
        );
        return true;
      }
      if (!mounted) return false;
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Invalid server response for nominee designation.',
      );
      return false;
    } catch (e) {
      if (!mounted) return false;
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
      return false;
    }
  }

  Future<bool> submitGrievance({
    required String reportedUserId,
    required String category,
    required String evidence,
  }) async {
    state = state.copyWith(isLoading: true, clearMessages: true);
    try {
      final res = await _client.post(
        '/api/v1/legal/grievance',
        body: {
          'reported_user_id': reportedUserId,
          'violation_category': category,
          'evidence_text': evidence,
        },
      );
      if (res['data'] != null && res['data'] is Map<String, dynamic>) {
        final data = res['data'] as Map<String, dynamic>;
        final created = GrievanceDossierModel(
          referenceId: data['dossier_reference_id']?.toString() ?? '',
          category: category,
          evidence: evidence,
          status: data['status']?.toString() ?? 'acknowledged',
          acknowledgmentSentAt: data['acknowledgment_sent_at']?.toString() ?? DateTime.now().toIso8601String(),
          statutoryResolutionDueAt: data['statutory_resolution_due_at']?.toString() ?? DateTime.now().add(const Duration(days: 15)).toIso8601String(),
          createdAt: DateTime.now().toIso8601String(),
        );
        if (!mounted) return true;
        state = state.copyWith(
          grievances: [created, ...state.grievances],
          isLoading: false,
          successMessage: 'Statutory grievance acknowledged (${created.referenceId}).',
        );
        return true;
      }
      if (!mounted) return false;
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Invalid server response for grievance submission.',
      );
      return false;
    } catch (e) {
      if (!mounted) return false;
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
      return false;
    }
  }

  Future<Map<String, dynamic>?> requestDataExport() async {
    state = state.copyWith(isExporting: true, clearMessages: true);
    try {
      final res = await _client.post('/api/v1/legal/data-export');
      final dynamic rawData = res['data'];
      final mapData = rawData is Map<String, dynamic> ? rawData : null;
      if (!mounted) return mapData;
      state = state.copyWith(
        isExporting: false,
        successMessage: 'Machine-readable export compiled successfully.',
      );
      return mapData;
    } catch (e) {
      if (!mounted) return null;
      state = state.copyWith(isExporting: false, errorMessage: e.toString());
      return null;
    }
  }
}

final vaultControllerProvider =
    StateNotifierProvider<VaultController, VaultState>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return VaultController(client);
});
