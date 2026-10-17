import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../../../../core/network/sanctuary_http_client.dart';
import '../../../../core/storage/secure_session_storage.dart';

const Object _unset = Object();

@immutable
class ProfileSetupState {
  final List<String?> photoUrls;
  final String? avatarUrl;
  final String? voiceSparkUrl;
  final double voiceSparkDuration;
  final String fullName;
  final String bio;
  final String profession;
  final String education;
  final String gender;
  final String interestedIn;
  final String contactBridgeType;
  final String contactBridgeHandle;
  final bool isUploadingMedia;
  final double uploadProgress;
  final bool isSubmitting;
  final String? errorMessage;
  final bool isKycVerified;
  final String? kycStatus;
  final String? kycStatusMessage;
  final bool isEditMode;

  const ProfileSetupState({
    this.photoUrls = const [null, null, null, null, null],
    this.avatarUrl,
    this.voiceSparkUrl,
    this.voiceSparkDuration = 0.0,
    this.fullName = '',
    this.bio = '',
    this.profession = '',
    this.education = '',
    this.gender = 'Woman',
    this.interestedIn = 'Men',
    this.contactBridgeType = 'whatsapp',
    this.contactBridgeHandle = '',
    this.isUploadingMedia = false,
    this.uploadProgress = 0.0,
    this.isSubmitting = false,
    this.errorMessage,
    this.isKycVerified = false,
    this.kycStatus,
    this.kycStatusMessage,
    this.isEditMode = false,
  });

  ProfileSetupState copyWith({
    List<String?>? photoUrls,
    Object? avatarUrl = _unset,
    Object? voiceSparkUrl = _unset,
    double? voiceSparkDuration,
    String? fullName,
    String? bio,
    String? profession,
    String? education,
    String? gender,
    String? interestedIn,
    String? contactBridgeType,
    String? contactBridgeHandle,
    bool? isUploadingMedia,
    double? uploadProgress,
    bool? isSubmitting,
    String? errorMessage,
    bool? isKycVerified,
    Object? kycStatus = _unset,
    Object? kycStatusMessage = _unset,
    bool? isEditMode,
  }) {
    return ProfileSetupState(
      photoUrls: photoUrls ?? this.photoUrls,
      avatarUrl: identical(avatarUrl, _unset) ? this.avatarUrl : avatarUrl as String?,
      voiceSparkUrl: identical(voiceSparkUrl, _unset) ? this.voiceSparkUrl : voiceSparkUrl as String?,
      voiceSparkDuration: voiceSparkDuration ?? this.voiceSparkDuration,
      fullName: fullName ?? this.fullName,
      bio: bio ?? this.bio,
      profession: profession ?? this.profession,
      education: education ?? this.education,
      gender: gender ?? this.gender,
      interestedIn: interestedIn ?? this.interestedIn,
      contactBridgeType: contactBridgeType ?? this.contactBridgeType,
      contactBridgeHandle: contactBridgeHandle ?? this.contactBridgeHandle,
      isUploadingMedia: isUploadingMedia ?? this.isUploadingMedia,
      uploadProgress: uploadProgress ?? this.uploadProgress,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      errorMessage: errorMessage,
      isKycVerified: isKycVerified ?? this.isKycVerified,
      kycStatus: identical(kycStatus, _unset) ? this.kycStatus : kycStatus as String?,
      kycStatusMessage: identical(kycStatusMessage, _unset) ? this.kycStatusMessage : kycStatusMessage as String?,
      isEditMode: isEditMode ?? this.isEditMode,
    );
  }
}

final rawHttpClientProvider = Provider<http.Client>((ref) {
  final client = http.Client();
  ref.onDispose(client.close);
  return client;
});

class ProfileSetupController extends StateNotifier<ProfileSetupState> {
  final SanctuaryHttpClient _client;
  final http.Client _rawHttpClient;
  final SecureSessionStorage _storage;

  ProfileSetupController({
    required SanctuaryHttpClient client,
    required http.Client rawHttpClient,
    required SecureSessionStorage storage,
  })  : _client = client,
        _rawHttpClient = rawHttpClient,
        _storage = storage,
        super(const ProfileSetupState());

  void updateTextFields({
    String? fullName,
    String? bio,
    String? profession,
    String? education,
    String? contactBridgeHandle,
  }) {
    state = state.copyWith(
      fullName: fullName ?? state.fullName,
      bio: bio ?? state.bio,
      profession: profession ?? state.profession,
      education: education ?? state.education,
      contactBridgeHandle: contactBridgeHandle ?? state.contactBridgeHandle,
      errorMessage: null,
    );
  }

  void setGender(String gender) {
    state = state.copyWith(gender: gender, errorMessage: null);
  }

  void setInterestedIn(String interestedIn) {
    state = state.copyWith(interestedIn: interestedIn, errorMessage: null);
  }

  void setContactBridgeType(String type) {
    state = state.copyWith(contactBridgeType: type, errorMessage: null);
  }

  /// Prepopulates state from existing seeker persona and sets edit mode.
  void initializeForEdit({Map<String, dynamic>? profileData}) {
    if (profileData != null) {
      final rawPhotos = profileData['photos'];
      final List<String?> photos = List<String?>.filled(5, null);
      if (rawPhotos is List) {
        for (var i = 0; i < rawPhotos.length && i < 5; i++) {
          photos[i] = rawPhotos[i]?.toString();
        }
      }

      state = state.copyWith(
        fullName: profileData['full_name']?.toString() ?? state.fullName,
        bio: profileData['bio']?.toString() ?? state.bio,
        profession: profileData['profession']?.toString() ?? state.profession,
        education: profileData['education']?.toString() ?? state.education,
        gender: profileData['gender']?.toString() ?? state.gender,
        interestedIn: profileData['interested_in']?.toString() ?? state.interestedIn,
        contactBridgeType: profileData['contact_bridge_type']?.toString() ?? state.contactBridgeType,
        contactBridgeHandle: profileData['contact_bridge_handle']?.toString() ?? state.contactBridgeHandle,
        avatarUrl: profileData['avatar_url']?.toString() ?? state.avatarUrl,
        photoUrls: (rawPhotos is List && rawPhotos.isNotEmpty) ? photos : state.photoUrls,
        voiceSparkUrl: profileData['voice_spark_url']?.toString() ?? state.voiceSparkUrl,
        voiceSparkDuration: (profileData['voice_spark_duration'] as num?)?.toDouble() ?? state.voiceSparkDuration,
        isEditMode: true,
        errorMessage: null,
      );
    } else {
      state = state.copyWith(isEditMode: true, errorMessage: null);
    }
  }

  void setEditMode(bool isEdit) {
    state = state.copyWith(isEditMode: isEdit, errorMessage: null);
  }

  /// Checks local secure storage and activates edit mode if profile is already completed.
  Future<bool> checkProfileCompletion() async {
    final isCompleted = await _storage.readCustomKey('is_profile_completed') == 'true';
    if (isCompleted) {
      state = state.copyWith(isEditMode: true);
    }
    return isCompleted;
  }

  /// Direct-to-R2 zero-bottleneck media upload pipeline for photo slots 1 to 5.
  Future<bool> uploadPhotoSlot(int slotIndex, List<int> imageBytes) async {
    if (slotIndex < 1 || slotIndex > 5) {
      state = state.copyWith(errorMessage: 'Invalid photo slot: must be between 1 and 5.');
      return false;
    }

    state = state.copyWith(
      isUploadingMedia: true,
      uploadProgress: 0.15,
      errorMessage: null,
    );

    try {
      // 1. Obtain S3v4 presigned URL from Sanctuary backend
      final presignedRes = await _client.post(
        '/api/v1/media/presigned-url',
        body: {
          'asset_type': 'moment',
          'slot_number': slotIndex,
          'content_type': 'image/webp',
          'file_size_bytes': imageBytes.length,
        },
      );

      final data = presignedRes['data'] is Map ? presignedRes['data'] as Map<String, dynamic> : presignedRes;
      final uploadUrl = data['upload_url'] as String?;
      final publicCdnUrl = data['public_cdn_url'] as String?;

      if (uploadUrl == null || publicCdnUrl == null) {
        state = state.copyWith(
          isUploadingMedia: false,
          errorMessage: 'Failed to acquire presigned R2 upload URL.',
        );
        return false;
      }

      state = state.copyWith(uploadProgress: 0.5);

      // 2. Direct binary HTTP PUT to Cloudflare R2
      final putResponse = await _rawHttpClient.put(
        Uri.parse(uploadUrl),
        headers: {'Content-Type': 'image/webp'},
        body: imageBytes,
      );

      if (putResponse.statusCode != 200 && putResponse.statusCode != 204) {
        state = state.copyWith(
          isUploadingMedia: false,
          errorMessage: 'Cloudflare R2 rejected media upload with HTTP ${putResponse.statusCode}.',
        );
        return false;
      }

      // 3. Update slot state with edge CDN URL
      final newPhotos = List<String?>.from(state.photoUrls);
      newPhotos[slotIndex - 1] = publicCdnUrl;

      state = state.copyWith(
        isUploadingMedia: false,
        uploadProgress: 1.0,
        photoUrls: newPhotos,
        avatarUrl: slotIndex == 1
            ? publicCdnUrl
            : (state.avatarUrl ?? newPhotos.firstWhere((p) => p != null, orElse: () => null)),
      );
      return true;
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(isUploadingMedia: false, errorMessage: e.message);
      return false;
    } catch (e) {
      state = state.copyWith(isUploadingMedia: false, errorMessage: e.toString());
      return false;
    }
  }

  /// Purges photo asset from Cloudflare R2 and removes URL reference from the slot.
  Future<bool> removePhotoSlot(int slotIndex) async {
    if (slotIndex < 1 || slotIndex > 5) {
      state = state.copyWith(errorMessage: 'Invalid photo slot: must be between 1 and 5.');
      return false;
    }

    try {
      await _client.delete('/api/v1/media/moment/$slotIndex');

      final newPhotos = List<String?>.from(state.photoUrls);
      final removedUrl = newPhotos[slotIndex - 1];
      newPhotos[slotIndex - 1] = null;

      String? newAvatar = state.avatarUrl;
      if (newAvatar == removedUrl) {
        newAvatar = newPhotos.firstWhere((p) => p != null, orElse: () => null);
      }

      state = state.copyWith(
        photoUrls: newPhotos,
        avatarUrl: newAvatar,
      );
      return true;
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(errorMessage: e.message);
      return false;
    } catch (e) {
      state = state.copyWith(errorMessage: e.toString());
      return false;
    }
  }

  /// Uploads up to 7.0 seconds of Voice Spark audio binary directly to Cloudflare R2.
  Future<bool> uploadVoiceSpark(List<int> audioBytes, double duration) async {
    state = state.copyWith(
      isUploadingMedia: true,
      uploadProgress: 0.15,
      errorMessage: null,
    );

    try {
      final presignedRes = await _client.post(
        '/api/v1/media/presigned-url',
        body: {
          'asset_type': 'voice_spark',
          'content_type': 'audio/m4a',
          'file_size_bytes': audioBytes.length,
        },
      );

      final data = presignedRes['data'] is Map ? presignedRes['data'] as Map<String, dynamic> : presignedRes;
      final uploadUrl = data['upload_url'] as String?;
      final publicCdnUrl = data['public_cdn_url'] as String?;

      if (uploadUrl == null || publicCdnUrl == null) {
        state = state.copyWith(
          isUploadingMedia: false,
          errorMessage: 'Failed to acquire presigned voice spark URL.',
        );
        return false;
      }

      state = state.copyWith(uploadProgress: 0.6);

      final putResponse = await _rawHttpClient.put(
        Uri.parse(uploadUrl),
        headers: {'Content-Type': 'audio/m4a'},
        body: audioBytes,
      );

      if (putResponse.statusCode != 200 && putResponse.statusCode != 204) {
        state = state.copyWith(
          isUploadingMedia: false,
          errorMessage: 'Cloudflare R2 rejected voice upload with HTTP ${putResponse.statusCode}.',
        );
        return false;
      }

      state = state.copyWith(
        isUploadingMedia: false,
        uploadProgress: 1.0,
        voiceSparkUrl: publicCdnUrl,
        voiceSparkDuration: duration,
      );
      return true;
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(isUploadingMedia: false, errorMessage: e.message);
      return false;
    } catch (e) {
      state = state.copyWith(isUploadingMedia: false, errorMessage: e.toString());
      return false;
    }
  }

  /// Validates profile requirements and submits complete seeker profile.
  /// If editing an existing profile (or profile is already marked completed in storage),
  /// calls PUT /api/v1/profile instead of POST /api/v1/profile/create.
  Future<bool> submitProfile() async {
    final name = state.fullName.trim();
    if (name.length < 2) {
      state = state.copyWith(errorMessage: 'Please enter your full name (minimum 2 characters).');
      return false;
    }

    final validPhotos = state.photoUrls.where((p) => p != null && p.isNotEmpty).map((p) => p!).toList();
    if (validPhotos.isEmpty) {
      state = state.copyWith(errorMessage: 'Please upload at least 1 photo to your sacred persona.');
      return false;
    }

    final isEditing = state.isEditMode;

    final handle = state.contactBridgeHandle.trim();
    if (!isEditing && handle.length < 3) {
      state = state.copyWith(errorMessage: 'Please provide a valid contact bridge handle (minimum 3 characters).');
      return false;
    }

    state = state.copyWith(isSubmitting: true, errorMessage: null);

    try {
      if (isEditing) {
        final updatePayload = <String, dynamic>{
          'full_name': name,
          'bio': state.bio.trim(),
          'profession': state.profession.trim(),
          'education': state.education.trim(),
          'photos': validPhotos,
          'avatar_url': state.avatarUrl ?? validPhotos.first,
          'interested_in': state.interestedIn,
        };

        await _client.put('/api/v1/profile', body: updatePayload);
      } else {
        final storedDob = await _storage.readCustomKey('user_dob');
        final payload = {
          'full_name': name,
          if (storedDob != null && storedDob.isNotEmpty) 'dob': storedDob,
          'gender': state.gender,
          'interested_in': state.interestedIn,
          'contact_bridge_type': state.contactBridgeType,
          'contact_bridge_raw': handle,
          'contact_bridge_handle': handle,
          'bio': state.bio.trim(),
          'profession': state.profession.trim(),
          'education': state.education.trim(),
          'photos': validPhotos,
          'avatar_url': state.avatarUrl ?? validPhotos.first,
          if (state.voiceSparkUrl != null) 'voice_spark_url': state.voiceSparkUrl,
          if (state.voiceSparkDuration > 0) 'voice_spark_duration': state.voiceSparkDuration,
        };

        await _client.post('/api/v1/profile/create', body: payload);
        await _storage.writeCustomKey('is_profile_completed', 'true');
      }

      state = state.copyWith(isSubmitting: false);
      return true;
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(isSubmitting: false, errorMessage: e.message);
      return false;
    } catch (e) {
      state = state.copyWith(isSubmitting: false, errorMessage: e.toString());
      return false;
    }
  }

  /// Uploads live selfie frame to ephemeral R2 path and triggers Groq facial liveness evaluation.
  Future<bool> submitKycLiveness(List<int> frameBytes) async {
    state = state.copyWith(isUploadingMedia: true, errorMessage: null);

    try {
      // 1. Obtain ephemeral upload presigned URL
      final presignedRes = await _client.post('/api/v1/kyc/presigned-upload');
      final data = presignedRes['data'] ?? presignedRes;
      final uploadUrl = data['upload_url'] as String;
      final objectKey = data['object_key'] as String;

      // 2. Direct binary PUT to Cloudflare R2
      final putResponse = await _rawHttpClient.put(
        Uri.parse(uploadUrl),
        headers: {'Content-Type': 'image/webp'},
        body: frameBytes,
      );

      if (putResponse.statusCode != 200 && putResponse.statusCode != 204) {
        state = state.copyWith(
          isUploadingMedia: false,
          errorMessage: 'R2 rejected ephemeral selfie upload with HTTP ${putResponse.statusCode}.',
        );
        return false;
      }

      // 3. Trigger Groq AI liveness verification
      final verifyRes = await _client.post(
        '/api/v1/kyc/verify-liveness',
        body: {'object_key': objectKey},
      );
      final verifyData = verifyRes['data'] ?? verifyRes;
      final status = verifyData['status'] as String? ?? 'rejected';
      final message = verifyData['message'] as String? ?? '';

      final isApproved = status == 'approved';
      state = state.copyWith(
        isUploadingMedia: false,
        isKycVerified: isApproved,
        kycStatus: status,
        kycStatusMessage: message,
      );
      return isApproved;
    } on SanctuaryClientException catch (e) {
      state = state.copyWith(
        isUploadingMedia: false,
        isKycVerified: false,
        kycStatus: 'rejected',
        kycStatusMessage: e.message,
        errorMessage: e.message,
      );
      return false;
    } catch (e) {
      state = state.copyWith(
        isUploadingMedia: false,
        isKycVerified: false,
        kycStatus: 'rejected',
        kycStatusMessage: e.toString(),
        errorMessage: e.toString(),
      );
      return false;
    }
  }
}

final profileSetupControllerProvider =
    StateNotifierProvider<ProfileSetupController, ProfileSetupState>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  final rawClient = ref.watch(rawHttpClientProvider);
  final storage = ref.watch(secureSessionStorageProvider);

  return ProfileSetupController(
    client: client,
    rawHttpClient: rawClient,
    storage: storage,
  );
});
