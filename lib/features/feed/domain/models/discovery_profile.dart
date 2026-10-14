import 'package:flutter/foundation.dart';

/// Candidate seeker card presented on the discovery deck with DPDP fuzzed coordinates.
@immutable
class DiscoveryProfile {
  final String id;
  final String fullName;
  final int age;
  final String gender;
  final String interestedIn;
  final String locationName;
  final String bio;
  final String profession;
  final String education;
  final int streakCount;
  final int boostPoints;
  final bool kycStatus;
  final bool isPhotoVeiled;
  final List<String> photos;
  final String? avatarUrl;
  final String? voiceSparkUrl;
  final String? voiceSparkPrompt;
  final double voiceSparkDuration;
  final bool isVoiceVerified;
  final double? distanceKm;

  const DiscoveryProfile({
    required this.id,
    required this.fullName,
    required this.age,
    required this.gender,
    required this.interestedIn,
    required this.locationName,
    required this.bio,
    required this.profession,
    required this.education,
    required this.streakCount,
    required this.boostPoints,
    required this.kycStatus,
    required this.isPhotoVeiled,
    required this.photos,
    this.avatarUrl,
    this.voiceSparkUrl,
    this.voiceSparkPrompt,
    this.voiceSparkDuration = 7.0,
    this.isVoiceVerified = false,
    this.distanceKm,
  });

  factory DiscoveryProfile.fromJson(Map<String, dynamic> json) {
    return DiscoveryProfile(
      id: json['id'] as String? ?? '',
      fullName: json['full_name'] as String? ?? '',
      age: (json['age'] as num?)?.toInt() ?? 25,
      gender: json['gender'] as String? ?? '',
      interestedIn: json['interested_in'] as String? ?? '',
      locationName: json['location_name'] as String? ?? 'Saket, Ayodhya',
      bio: json['bio'] as String? ?? '',
      profession: json['profession'] as String? ?? '',
      education: json['education'] as String? ?? '',
      streakCount: (json['streak_count'] as num?)?.toInt() ?? 0,
      boostPoints: (json['boost_points'] as num?)?.toInt() ?? 0,
      kycStatus: json['kyc_status'] as bool? ?? false,
      isPhotoVeiled: json['is_photo_veiled'] as bool? ?? true,
      photos: (json['photos'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      avatarUrl: json['avatar_url'] as String?,
      voiceSparkUrl: json['voice_spark_url'] as String?,
      voiceSparkPrompt: json['voice_spark_prompt'] as String?,
      voiceSparkDuration:
          (json['voice_spark_duration'] as num?)?.toDouble() ?? 7.0,
      isVoiceVerified: json['is_voice_verified'] as bool? ?? false,
      distanceKm: (json['distance_km'] as num?)?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'full_name': fullName,
        'age': age,
        'gender': gender,
        'interested_in': interestedIn,
        'location_name': locationName,
        'bio': bio,
        'profession': profession,
        'education': education,
        'streak_count': streakCount,
        'boost_points': boostPoints,
        'kyc_status': kycStatus,
        'is_photo_veiled': isPhotoVeiled,
        'photos': photos,
        'avatar_url': avatarUrl,
        'voice_spark_url': voiceSparkUrl,
        'voice_spark_prompt': voiceSparkPrompt,
        'voice_spark_duration': voiceSparkDuration,
        'is_voice_verified': isVoiceVerified,
        'distance_km': distanceKm,
      };

  DiscoveryProfile copyWith({
    String? id,
    String? fullName,
    int? age,
    String? gender,
    String? interestedIn,
    String? locationName,
    String? bio,
    String? profession,
    String? education,
    int? streakCount,
    int? boostPoints,
    bool? kycStatus,
    bool? isPhotoVeiled,
    List<String>? photos,
    String? avatarUrl,
    String? voiceSparkUrl,
    String? voiceSparkPrompt,
    double? voiceSparkDuration,
    bool? isVoiceVerified,
    double? distanceKm,
  }) {
    return DiscoveryProfile(
      id: id ?? this.id,
      fullName: fullName ?? this.fullName,
      age: age ?? this.age,
      gender: gender ?? this.gender,
      interestedIn: interestedIn ?? this.interestedIn,
      locationName: locationName ?? this.locationName,
      bio: bio ?? this.bio,
      profession: profession ?? this.profession,
      education: education ?? this.education,
      streakCount: streakCount ?? this.streakCount,
      boostPoints: boostPoints ?? this.boostPoints,
      kycStatus: kycStatus ?? this.kycStatus,
      isPhotoVeiled: isPhotoVeiled ?? this.isPhotoVeiled,
      photos: photos ?? this.photos,
      avatarUrl: avatarUrl ?? this.avatarUrl,
      voiceSparkUrl: voiceSparkUrl ?? this.voiceSparkUrl,
      voiceSparkPrompt: voiceSparkPrompt ?? this.voiceSparkPrompt,
      voiceSparkDuration: voiceSparkDuration ?? this.voiceSparkDuration,
      isVoiceVerified: isVoiceVerified ?? this.isVoiceVerified,
      distanceKm: distanceKm ?? this.distanceKm,
    );
  }
}
