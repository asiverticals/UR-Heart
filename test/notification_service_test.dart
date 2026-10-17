import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/services/notification_service.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TestSecureStorage extends Fake implements FlutterSecureStorage {
  final Map<String, String> _data = {};

  @override
  Future<void> write({
    required String key,
    required String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value != null) {
      _data[key] = value;
    } else {
      _data.remove(key);
    }
  }

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    return _data[key];
  }
}

class FakeHttpClient extends http.BaseClient {
  Future<http.Response> Function(http.Request request)? handler;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (request is http.Request && handler != null) {
      final response = await handler!(request);
      return http.StreamedResponse(
        Stream.value(utf8.encode(response.body)),
        response.statusCode,
        headers: response.headers,
      );
    }
    return http.StreamedResponse(
      Stream.value(utf8.encode('{}')),
      200,
      headers: {'content-type': 'application/json'},
    );
  }
}

void main() {
  group('Phase 6 — Chunk 6.3: Flutter NotificationService Unit Tests', () {
    late TestSecureStorage storage;
    late SecureSessionStorage sessionStorage;
    late FakeHttpClient fakeHttp;
    late SanctuaryHttpClient httpClient;
    late NotificationService service;

    setUp(() {
      storage = TestSecureStorage();
      sessionStorage = SecureSessionStorage(storage: storage);
      fakeHttp = FakeHttpClient();
      httpClient = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      service = NotificationService(httpClient);
    });

    test('Test 1: syncDeviceToken formats registration payload with platform enum and installationId', () async {
      http.Request? capturedRequest;
      fakeHttp.handler = (req) async {
        capturedRequest = req;
        return http.Response(
          jsonEncode({
            'data': {'registered': true},
            'message': 'Token registered',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      };

      final result = await service.syncDeviceToken(
        'fcm_token_device_xyz123',
        installationId: 'install_uuid_888',
      );

      expect(result, isTrue);
      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.method, equals('POST'));
      expect(capturedRequest!.url.path, equals('/api/v1/notifications/device-token'));

      final body = jsonDecode(capturedRequest!.body) as Map<String, dynamic>;
      expect(body['token'], equals('fcm_token_device_xyz123'));
      expect(body['installation_id'], equals('install_uuid_888'));
      expect(['android', 'ios', 'web'], contains(body['platform']));
    });

    test('Test 2: clearDeviceToken dispatches DELETE request with token', () async {
      http.Request? capturedRequest;
      fakeHttp.handler = (req) async {
        capturedRequest = req;
        return http.Response(
          jsonEncode({
            'data': {'unregistered': true},
            'message': 'Token unregistered',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      };

      final result = await service.clearDeviceToken('fcm_token_device_xyz123');

      expect(result, isTrue);
      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.method, equals('DELETE'));
      expect(capturedRequest!.url.path, equals('/api/v1/notifications/device-token'));

      final body = jsonDecode(capturedRequest!.body) as Map<String, dynamic>;
      expect(body['token'], equals('fcm_token_device_xyz123'));
    });

    test('Test 3: updatePushPreferences sends PUT request with updated flag', () async {
      http.Request? capturedRequest;
      fakeHttp.handler = (req) async {
        capturedRequest = req;
        return http.Response(
          jsonEncode({
            'data': {'push_notifications_enabled': false},
            'message': 'Preferences updated',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      };

      final result = await service.updatePushPreferences(false);

      expect(result, isTrue);
      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.method, equals('PUT'));
      expect(capturedRequest!.url.path, equals('/api/v1/notifications/preferences'));

      final body = jsonDecode(capturedRequest!.body) as Map<String, dynamic>;
      expect(body['push_enabled'], isFalse);
    });

    testWidgets('Test 4: handleNotificationTap deep links to /chat-dialogue with extra match_id', (tester) async {
      String? pushedLocation;
      Object? pushedExtra;

      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(path: '/', builder: (_, __) => const Scaffold(body: Text('Home'))),
          GoRoute(
            path: '/chat-dialogue',
            builder: (context, state) {
              pushedLocation = '/chat-dialogue';
              pushedExtra = state.extra;
              return const Scaffold(body: Text('ChatDialogue'));
            },
          ),
        ],
      );

      await tester.pumpWidget(MaterialApp.router(routerConfig: router));
      await tester.pumpAndSettle();

      final payload = {
        'type': 'chat_message',
        'match_id': 'match-uuid-5555',
      };

      service.handleNotificationTap(payload, router);
      await tester.pumpAndSettle();

      expect(pushedLocation, equals('/chat-dialogue'));
      expect(pushedExtra, isA<Map<String, dynamic>>());
      expect((pushedExtra as Map<String, dynamic>)['match_id'], equals('match-uuid-5555'));
    });

    test('Test 5: Channels configuration adheres to dual-channel specifications', () {
      final channels = service.registeredChannels;
      expect(channels.length, equals(2));

      final kinship = channels.firstWhere((c) => c.id == 'channel_kinship_dialogue');
      expect(kinship.name, equals('Kinship Dialogues'));
      expect(kinship.importance, equals('high'));
      expect(kinship.enableVibration, isTrue);

      final mindful = channels.firstWhere((c) => c.id == 'channel_mindful_rhythm');
      expect(mindful.name, equals('Mindful Rhythms'));
      expect(mindful.importance, equals('low'));
      expect(mindful.enableVibration, isFalse);
    });

    test('Test 6: initialize marks service as initialized and syncs device token', () async {
      http.Request? capturedRequest;
      fakeHttp.handler = (req) async {
        capturedRequest = req;
        return http.Response(
          jsonEncode({
            'data': {'registered': true},
            'message': 'Token registered',
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      };

      expect(service.isInitialized, isFalse);
      final result = await service.initialize(
        fcmToken: 'fcm_token_device_xyz123',
        installationId: 'install_uuid_888',
      );

      expect(result, isTrue);
      expect(service.isInitialized, isTrue);
      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.method, equals('POST'));
      expect(capturedRequest!.url.path, equals('/api/v1/notifications/device-token'));
    });
  });
}
