import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/services/window_security_service.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/settings/presentation/screens/sanctuary_settings_screen.dart';

class MockIncinerationStorage extends Fake implements SecureSessionStorage {
  bool isSessionCleared = false;

  @override
  Future<void> clearSession() async {
    isSessionCleared = true;
  }
}

class MockIncinerationHttpClient extends Fake implements SanctuaryHttpClient {
  bool deleteCalled = false;
  String? deletedPath;
  Map<String, dynamic>? deletedBody;

  @override
  Duration get requestTimeout => const Duration(seconds: 5);

  @override
  Future<Map<String, dynamic>> delete(String path, {Map<String, dynamic>? body}) async {
    deleteCalled = true;
    deletedPath = path;
    deletedBody = body;
    return {
      'success': true,
      'data': {
        'status': 'incinerated',
        'message': 'Sacred identity permanently erased from sanctuary.',
        'certificate': 'DPDP-INCINERATE-TEST999',
      },
    };
  }
}

Widget buildTestApp({
  required MockIncinerationHttpClient client,
  required MockIncinerationStorage storage,
}) {
  final router = GoRouter(
    initialLocation: '/settings',
    routes: [
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SanctuarySettingsScreen(),
      ),
      GoRoute(
        path: '/consent',
        builder: (context, state) => const Scaffold(
          body: Center(
            child: Text('ConsentScreen'),
          ),
        ),
      ),
    ],
  );

  return ProviderScope(
    overrides: [
      sanctuaryHttpClientProvider.overrideWithValue(client),
      secureSessionStorageProvider.overrideWithValue(storage),
    ],
    child: MaterialApp.router(
      routerConfig: router,
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      WindowSecurityService.channel,
      (MethodCall call) async {
        if (call.method == 'enableSecureWindow' || call.method == 'disableSecureWindow') {
          return true;
        }
        return null;
      },
    );
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(WindowSecurityService.channel, null);
  });

  testWidgets(
    'Test 1: AccountIncinerationDialog keeps confirmation button disabled until both the 5-second timer completes and "PERMANENTLY INCINERATE" is typed',
    (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final mockClient = MockIncinerationHttpClient();
      final mockStorage = MockIncinerationStorage();

      await tester.pumpWidget(buildTestApp(client: mockClient, storage: mockStorage));
      await tester.pumpAndSettle();

      // Tap settings tile to open incineration modal
      final tile = find.byKey(const Key('incinerate_persona_tile'));
      expect(tile, findsOneWidget);
      await tester.tap(tile);
      await tester.pump();

      // Verify Dialog header and content
      expect(find.text('Incinerate Sacred Persona'), findsWidgets);
      expect(find.textContaining('Section 12 DPDP Act 2023 Erasure'), findsOneWidget);

      final confirmBtnFinder = find.byKey(const Key('confirm_incineration_button'));
      expect(confirmBtnFinder, findsOneWidget);

      ElevatedButton getButton() => tester.widget<ElevatedButton>(confirmBtnFinder);

      // 1. Initial State: Button must be disabled (lockout active, phrase empty)
      expect(getButton().onPressed, isNull);
      expect(find.textContaining('Mindfulness lockout active:'), findsOneWidget);

      // 2. Type exact phrase while timer still running: Button remains disabled
      final phraseField = find.byKey(const Key('incineration_phrase_field'));
      expect(phraseField, findsOneWidget);
      await tester.enterText(phraseField, 'PERMANENTLY INCINERATE');
      await tester.pump();
      expect(getButton().onPressed, isNull);

      // 3. Advance time through the 5-second mindfulness countdown
      for (int i = 0; i < 5; i++) {
        await tester.pump(const Duration(seconds: 1));
      }
      await tester.pump();

      // Now timer is 0 AND phrase is exact match: Button must be ENABLED
      expect(getButton().onPressed, isNotNull);
      expect(find.text('Confirm Permanent Incineration'), findsOneWidget);

      // 4. Invalidate phrase: Button must immediately disable again
      await tester.enterText(phraseField, 'delete');
      await tester.pump();
      expect(getButton().onPressed, isNull);

      // 5. Restore phrase: Button re-enables
      await tester.enterText(phraseField, 'PERMANENTLY INCINERATE');
      await tester.pump();
      expect(getButton().onPressed, isNotNull);
    },
  );

  testWidgets(
    'Test 2: Tapping confirmed incineration triggers session wipe and navigates to /consent',
    (tester) async {
      tester.view.physicalSize = const Size(800, 1400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final mockClient = MockIncinerationHttpClient();
      final mockStorage = MockIncinerationStorage();

      await tester.pumpWidget(buildTestApp(client: mockClient, storage: mockStorage));
      await tester.pumpAndSettle();

      // Open modal
      await tester.tap(find.byKey(const Key('incinerate_persona_tile')));
      await tester.pump();

      // Wait out 5-second mindfulness lockout step-by-step
      for (int i = 0; i < 5; i++) {
        await tester.pump(const Duration(seconds: 1));
      }
      await tester.pump();

      // Enter required uppercase phrase
      final phraseField = find.byKey(const Key('incineration_phrase_field'));
      await tester.enterText(phraseField, 'PERMANENTLY INCINERATE');
      await tester.pump();

      final confirmBtn = find.byKey(const Key('confirm_incineration_button'));
      expect(tester.widget<ElevatedButton>(confirmBtn).onPressed, isNotNull);

      // Tap Confirm and pump async transitions
      await tester.tap(confirmBtn);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(milliseconds: 300));

      // Verify HTTP delete dispatched
      expect(mockClient.deleteCalled, isTrue);
      expect(mockClient.deletedPath, '/api/v1/legal/account');
      expect(mockClient.deletedBody?['confirmation_phrase'], 'PERMANENTLY INCINERATE');

      // Verify hardware keystore session wipe called
      expect(mockStorage.isSessionCleared, isTrue);

      // Verify navigation to /consent
      expect(find.text('ConsentScreen'), findsOneWidget);
    },
  );
}
