import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../network/sanctuary_http_client.dart';

class NotificationChannelConfig {
  final String id;
  final String name;
  final String description;
  final String importance;
  final bool enableVibration;

  const NotificationChannelConfig({
    required this.id,
    required this.name,
    required this.description,
    required this.importance,
    this.enableVibration = false,
  });
}

final notificationServiceProvider = Provider<NotificationService>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return NotificationService(client);
});

class NotificationService {
  final SanctuaryHttpClient _client;
  bool _isInitialized = false;

  bool get isInitialized => _isInitialized;

  static const channelKinshipDialogue = NotificationChannelConfig(
    id: 'channel_kinship_dialogue',
    name: 'Kinship Dialogues',
    description: 'Urgent incoming dialogue reflections',
    importance: 'high',
    enableVibration: true,
  );

  static const channelMindfulRhythm = NotificationChannelConfig(
    id: 'channel_mindful_rhythm',
    name: 'Mindful Rhythms',
    description: 'Streak reminders and morning harvests',
    importance: 'low',
    enableVibration: false,
  );

  List<NotificationChannelConfig> get registeredChannels => [
    channelKinshipDialogue,
    channelMindfulRhythm,
  ];

  NotificationService(this._client);

  /// Initializes the notification service and synchronizes device FCM token if provided.
  Future<bool> initialize({String? fcmToken, String? installationId}) async {
    _isInitialized = true;
    if (fcmToken != null && fcmToken.isNotEmpty) {
      try {
        return await syncDeviceToken(fcmToken, installationId: installationId);
      } catch (_) {
        return false;
      }
    }
    return true;
  }

  String get currentPlatform {
    if (kIsWeb) return 'web';
    if (Platform.isAndroid) return 'android';
    if (Platform.isIOS) return 'ios';
    return 'web';
  }

  Future<bool> syncDeviceToken(String fcmToken, {String? installationId}) async {
    final response = await _client.post(
      '/api/v1/notifications/device-token',
      body: {
        'token': fcmToken,
        'platform': currentPlatform,
        if (installationId != null) 'installation_id': installationId,
      },
    );
    return response['data']?['registered'] == true;
  }

  Future<bool> clearDeviceToken(String fcmToken) async {
    final response = await _client.delete(
      '/api/v1/notifications/device-token',
      body: {'token': fcmToken},
    );
    return response['data']?['unregistered'] == true;
  }

  Future<bool> updatePushPreferences(bool enabled) async {
    final response = await _client.put(
      '/api/v1/notifications/preferences',
      body: {'push_enabled': enabled},
    );
    return response['data']?['push_notifications_enabled'] == enabled;
  }

  void handleNotificationTap(Map<String, dynamic> data, GoRouter router) {
    if (data['type'] == 'chat_message' && data['match_id'] != null) {
      final matchId = data['match_id'].toString();
      router.push('/chat-dialogue', extra: {'match_id': matchId});
    }
  }
}
