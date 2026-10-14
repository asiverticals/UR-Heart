import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';
import '../../../../core/services/device_fingerprint_service.dart';
import '../../../../core/storage/secure_session_storage.dart';

@immutable
class CurrentUser {
  final String id;
  final String role;
  final String? email;

  const CurrentUser({
    required this.id,
    required this.role,
    this.email,
  });
}

final currentUserProvider = StateProvider<CurrentUser?>((ref) => null);

@immutable
class AuthState {
  final bool isLoading;
  final bool isUnderageQuarantined;
  final DateTime? quarantineUntil;
  final DateTime? selectedDob;
  final int? calculatedAge;
  final bool isEligible;
  final bool isServerApproved;
  final String? magicLinkSentEmail;
  final String? errorMessage;

  const AuthState({
    this.isLoading = false,
    this.isUnderageQuarantined = false,
    this.quarantineUntil,
    this.selectedDob,
    this.calculatedAge,
    this.isEligible = false,
    this.isServerApproved = false,
    this.magicLinkSentEmail,
    this.errorMessage,
  });

  AuthState copyWith({
    bool? isLoading,
    bool? isUnderageQuarantined,
    DateTime? quarantineUntil,
    DateTime? selectedDob,
    int? calculatedAge,
    bool? isEligible,
    bool? isServerApproved,
    String? magicLinkSentEmail,
    String? errorMessage,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      isUnderageQuarantined: isUnderageQuarantined ?? this.isUnderageQuarantined,
      quarantineUntil: quarantineUntil ?? this.quarantineUntil,
      selectedDob: selectedDob ?? this.selectedDob,
      calculatedAge: calculatedAge ?? this.calculatedAge,
      isEligible: isEligible ?? this.isEligible,
      isServerApproved: isServerApproved ?? this.isServerApproved,
      magicLinkSentEmail: magicLinkSentEmail ?? this.magicLinkSentEmail,
      errorMessage: errorMessage,
    );
  }
}

class AuthController extends StateNotifier<AuthState> {
  final SanctuaryHttpClient _client;
  final SecureSessionStorage _storage;
  final DeviceFingerprintService _fingerprintService;
  int _verificationGeneration = 0;

  AuthController({
    required SanctuaryHttpClient client,
    required SecureSessionStorage storage,
    required DeviceFingerprintService fingerprintService,
  })  : _client = client,
        _storage = storage,
        _fingerprintService = fingerprintService,
        super(const AuthState());

  /// Calculates chronological age in years accurately taking month and day into account.
  void updateDob(DateTime dob, {DateTime? referenceDate}) {
    _verificationGeneration++;
    final today = referenceDate ?? DateTime.now();
    var age = today.year - dob.year;
    if (today.month < dob.month || (today.month == dob.month && today.day < dob.day)) {
      age--;
    }
    state = state.copyWith(
      selectedDob: dob,
      calculatedAge: age,
      isEligible: age >= 18,
      isServerApproved: false,
      errorMessage: null,
    );
  }

  /// Evaluates 18+ statutory age gate and records hardware quarantine on violations.
  Future<bool> verifyAgeAndRegisterIntent() async {
    final dob = state.selectedDob;
    if (dob == null) {
      state = state.copyWith(errorMessage: 'Please select your date of birth.');
      return false;
    }

    final generation = ++_verificationGeneration;
    state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final fingerprint = await _fingerprintService.getOrCreateFingerprint();
      final formattedDob =
          '${dob.year.toString().padLeft(4, '0')}-${dob.month.toString().padLeft(2, '0')}-${dob.day.toString().padLeft(2, '0')}';

      final response = await _client.post(
        '/api/v1/auth/register-intent',
        body: {
          'dob': formattedDob,
          'device_fingerprint': fingerprint,
        },
      );

      // Discard response if DOB changed or a newer verification was started
      if (generation != _verificationGeneration || state.selectedDob != dob) {
        return false;
      }

      final isEligible = response['data']?['eligible'] == true || response['eligible'] == true;
      if (isEligible) {
        await _storage.writeCustomKey('user_dob', formattedDob);
      }

      // Recheck generation and selected DOB after storage write to prevent race conditions
      if (generation != _verificationGeneration || state.selectedDob != dob) {
        if (isEligible) {
          await _storage.deleteCustomKey('user_dob');
        }
        return false;
      }

      state = state.copyWith(
        isLoading: false,
        isEligible: isEligible,
        isServerApproved: isEligible,
        isUnderageQuarantined: false,
      );
      return isEligible;
    } on SanctuaryClientException catch (e) {
      if (generation != _verificationGeneration || state.selectedDob != dob) {
        return false;
      }
      if (e.errorCode == 'UNDERAGE_QUARANTINE_TRIGGERED') {
        final quarantineDate = DateTime.now().add(const Duration(days: 180));
        state = state.copyWith(
          isLoading: false,
          isEligible: false,
          isServerApproved: false,
          isUnderageQuarantined: true,
          quarantineUntil: quarantineDate,
          errorMessage: e.message,
        );
        return false;
      }
      state = state.copyWith(
        isLoading: false,
        isServerApproved: false,
        errorMessage: e.message,
      );
      return false;
    } catch (e) {
      if (generation != _verificationGeneration || state.selectedDob != dob) {
        return false;
      }
      state = state.copyWith(
        isLoading: false,
        isServerApproved: false,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  /// Dispatches passwordless cryptographic magic link.
  Future<bool> sendMagicLink(String email) async {
    final trimmed = email.trim();
    if (trimmed.isEmpty || !trimmed.contains('@')) {
      state = state.copyWith(errorMessage: 'Please enter a valid email address.');
      return false;
    }

    state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      await _client.post(
        '/api/v1/auth/send-magic-link',
        body: {'email': trimmed},
      );
      state = state.copyWith(
        isLoading: false,
        magicLinkSentEmail: trimmed,
        errorMessage: null,
      );
      return true;
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.message);
      return false;
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
      return false;
    }
  }

  /// Exchanges Google OAuth2 token for authentic Sanctuary session tokens.
  Future<bool> syncGoogleUser(String idToken) async {
    state = state.copyWith(isLoading: true, errorMessage: null);

    try {
      final fingerprint = await _fingerprintService.getOrCreateFingerprint();
      final res = await _client.post(
        '/api/v1/auth/google-sync',
        body: {
          'id_token': idToken,
          'installation_uuid': fingerprint,
        },
      );

      final accessToken = res['access_token'] as String?;
      final refreshToken = res['refresh_token'] as String?;
      final userId = res['user_id']?.toString();
      final role = res['role'] as String? ?? 'user';

      if (accessToken != null &&
          accessToken.isNotEmpty &&
          refreshToken != null &&
          refreshToken.isNotEmpty &&
          userId != null &&
          userId.isNotEmpty) {
        await _storage.persistSession(
          accessToken: accessToken,
          refreshToken: refreshToken,
          userId: userId,
          role: role,
        );
        state = state.copyWith(isLoading: false);
        return true;
      }
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Invalid authentication payload received: missing tokens or user ID.',
      );
      return false;
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.message);
      return false;
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
      return false;
    }
  }
}

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>((ref) {
  final storage = ref.watch(secureSessionStorageProvider);
  final client = ref.watch(sanctuaryHttpClientProvider);
  final fingerprintService = ref.watch(deviceFingerprintServiceProvider);

  return AuthController(
    client: client,
    storage: storage,
    fingerprintService: fingerprintService,
  );
});
