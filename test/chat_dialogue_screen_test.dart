import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/services/window_security_service.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/core/theme/glass_tokens.dart';
import 'package:ur_heart/core/theme/widgets/sanctuary_glass_container.dart';
import 'package:ur_heart/features/auth/presentation/controllers/auth_controller.dart';
import 'package:ur_heart/features/chat/data/chat_websocket_service.dart';
import 'package:ur_heart/features/chat/domain/models/chat_message.dart';
import 'package:ur_heart/features/chat/presentation/controllers/chat_dialogue_controller.dart';
import 'package:ur_heart/features/chat/presentation/screens/chat_dialogue_screen.dart';
import 'package:ur_heart/features/chat/presentation/widgets/pass_with_grace_dialog.dart';

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

class FakeHttpClient extends Fake implements http.Client {
  Future<http.Response> Function(Uri url, Map<String, String>? headers)? onGet;
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onPost;

  @override
  Future<http.Response> get(Uri url, {Map<String, String>? headers}) async {
    if (onGet != null) return onGet!(url, headers);
    return http.Response('{"data": []}', 200);
  }

  @override
  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    dynamic encoding,
  }) async {
    if (onPost != null) return onPost!(url, headers, body);
    return http.Response('{"data": {"success": true}}', 200);
  }
}

class FakeChatWebSocketService extends Fake implements ChatWebSocketService {
  final StreamController<Map<String, dynamic>> _controller =
      StreamController<Map<String, dynamic>>.broadcast();

  final List<Map<String, dynamic>> sentFrames = [];

  @override
  Stream<Map<String, dynamic>> get eventStream => _controller.stream;

  @override
  bool get isConnected => true;

  @override
  Future<void> connect({String? customTicket}) async {}

  @override
  void sendMessage({
    required String matchId,
    required String recipientId,
    required String encryptedText,
    required String clientId,
  }) {
    sentFrames.add({
      'type': 'message',
      'match_id': matchId,
      'recipient_id': recipientId,
      'encrypted_text': encryptedText,
      'client_id': clientId,
    });
  }

  @override
  void sendTyping({
    required String matchId,
    required String recipientId,
    required bool isTyping,
  }) {
    sentFrames.add({
      'type': 'typing',
      'match_id': matchId,
      'recipient_id': recipientId,
      'is_typing': isTyping,
    });
  }

  @override
  void sendReadReceipt({
    required String matchId,
    required String recipientId,
  }) {
    sentFrames.add({
      'type': 'read_receipt',
      'match_id': matchId,
      'recipient_id': recipientId,
    });
  }

  @override
  void disconnect() {}

  @override
  void dispose() {
    _controller.close();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late TestSecureStorage fakeStorage;
  late SecureSessionStorage sessionStorage;
  late FakeHttpClient fakeHttpClient;
  late SanctuaryHttpClient httpClient;
  late FakeChatWebSocketService fakeWsService;
  final List<MethodCall> methodCalls = [];

  setUp(() {
    fakeStorage = TestSecureStorage();
    sessionStorage = SecureSessionStorage(storage: fakeStorage);
    fakeHttpClient = FakeHttpClient();
    httpClient = SanctuaryHttpClient(sessionStorage, client: fakeHttpClient);
    fakeWsService = FakeChatWebSocketService();

    methodCalls.clear();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      WindowSecurityService.channel,
      (MethodCall call) async {
        methodCalls.add(call);
        return true;
      },
    );
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(WindowSecurityService.channel, null);
    sessionStorage.dispose();
    fakeWsService.dispose();
  });

  Widget createChatScreen({
    required String matchId,
    required String peerId,
    ChatDialogueController? customController,
  }) {
    return ProviderScope(
      overrides: [
        sanctuaryHttpClientProvider.overrideWithValue(httpClient),
        chatWebSocketServiceProvider.overrideWithValue(fakeWsService),
        currentUserProvider.overrideWith(
          (ref) => const CurrentUser(id: 'current_user_1', role: 'seeker'),
        ),
        if (customController != null)
          chatDialogueControllerProvider(matchId).overrideWith((ref) => customController),
      ],
      child: MaterialApp(
        home: ChatDialogueScreen(
          matchId: matchId,
          peerId: peerId,
          peerName: 'Aarav Seeker',
        ),
      ),
    );
  }

  testWidgets(
      'Test 1: ChatDialogueScreen triggers enforceWindowProtection on mount and relaxWindowProtection on unmount',
      (tester) async {
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    addTearDown(() => debugDefaultTargetPlatformOverride = null);

    const matchId = 'm_test_1';
    const peerId = 'p_test_1';

    await tester.pumpWidget(createChatScreen(matchId: matchId, peerId: peerId));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // Verify enableSecureWindow was called
    expect(methodCalls.map((c) => c.method), contains('enableSecureWindow'));

    // Unmount screen
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // Verify disableSecureWindow was called
    expect(methodCalls.map((c) => c.method), contains('disableSecureWindow'));

    debugDefaultTargetPlatformOverride = null;
  });

  testWidgets(
      'Test 2: Input bar accepts text, prevents sending empty strings, and renders sender bubbles with terracotta styling',
      (tester) async {
    const matchId = 'm_test_2';
    const peerId = 'p_test_2';

    // Mock backend messages endpoint
    fakeHttpClient.onGet = (url, headers) async {
      if (url.path.contains('/api/v1/chat/messages/')) {
        return http.Response(
          jsonEncode({
            'data': [
              {
                'id': 1,
                'match_id': matchId,
                'sender_id': 'current_user_1',
                'encrypted_text': 'Hello soul companion',
                'status': 'delivered',
                'created_at': DateTime.now().toIso8601String(),
              },
              {
                'id': 2,
                'match_id': matchId,
                'sender_id': peerId,
                'encrypted_text': 'Peace and gratitude',
                'status': 'delivered',
                'created_at': DateTime.now().toIso8601String(),
              },
            ],
          }),
          200,
        );
      }
      return http.Response('{"data": []}', 200);
    };

    final controller = ChatDialogueController(
      matchId: matchId,
      httpClient: httpClient,
      wsService: fakeWsService,
      currentUserId: 'current_user_1',
      initialState: ChatDialogueState(
        messages: [
          ChatMessage(
            id: 1,
            matchId: matchId,
            senderId: 'current_user_1',
            encryptedText: 'Hello soul companion',
            status: 'delivered',
            createdAt: DateTime.now(),
          ),
          ChatMessage(
            id: 2,
            matchId: matchId,
            senderId: peerId,
            encryptedText: 'Peace and gratitude',
            status: 'delivered',
            createdAt: DateTime.now(),
          ),
        ],
      ),
    );

    await tester.pumpWidget(createChatScreen(
      matchId: matchId,
      peerId: peerId,
      customController: controller,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // Verify messages rendered
    expect(find.text('Hello soul companion'), findsOneWidget);
    expect(find.text('Peace and gratitude'), findsOneWidget);

    // Verify sender bubble has terracotta styling
    final glassContainers = tester.widgetList<SanctuaryGlassContainer>(
      find.byType(SanctuaryGlassContainer),
    );
    final hasTerracotta = glassContainers.any((c) {
      final gradient = c.customBorderGradient;
      if (gradient is LinearGradient) {
        return gradient.colors.contains(SanctuaryGlassTokens.brandTerracotta);
      }
      return false;
    });
    expect(hasTerracotta, isTrue);

    // Enter empty string and verify no new message is appended
    final inputFinder = find.byType(TextField);
    expect(inputFinder, findsOneWidget);

    final sendButtonFinder = find.byIcon(Icons.arrow_upward_rounded);
    expect(sendButtonFinder, findsOneWidget);

    await tester.enterText(inputFinder, '   ');
    await tester.tap(sendButtonFinder);
    await tester.pump();
    expect(controller.state.messages.length, equals(2));

    // Enter valid text and send
    await tester.enterText(inputFinder, 'Let us speak with mindfulness.');
    await tester.tap(sendButtonFinder);
    await tester.pump();

    expect(controller.state.messages.length, equals(3));
    expect(find.text('Let us speak with mindfulness.'), findsOneWidget);
    expect(fakeWsService.sentFrames.any((f) => f['encrypted_text'] == 'Let us speak with mindfulness.'), isTrue);
  });

  testWidgets(
      'Test 3: Opening PassWithGraceDialog displays the 3 closure templates and dispatches closure callback',
      (tester) async {
    tester.view.physicalSize = const Size(800, 1100);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    String? selectedKey;
    String? notePassed;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () {
                PassWithGraceDialog.show(
                  context,
                  onConfirmClosure: (key, note) async {
                    selectedKey = key;
                    notePassed = note;
                    return true;
                  },
                );
              },
              child: const Text('Open Dialog'),
            ),
          ),
        ),
      ),
    );

    // Open dialog
    await tester.tap(find.text('Open Dialog'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Verify Title & Subtitle
    expect(find.text('Part Ways with Grace'), findsOneWidget);
    expect(
      find.text('Ghosting shocks the spirit. Select a mindful closure thought to conclude this kinship with dignity.'),
      findsOneWidget,
    );

    // Verify all 3 templates are visible
    expect(find.text('Paths Diverge'), findsOneWidget);
    expect(find.text('"Our paths diverge, but I honor our shared dialogue."'), findsOneWidget);

    expect(find.text('Differing Rhythms'), findsOneWidget);
    expect(find.text('"I felt our core rhythms differ, wishing you clarity."'), findsOneWidget);

    expect(find.text('Quiet Solitude'), findsOneWidget);
    expect(find.text('"Taking time for quiet solitude; bowing out with gratitude."'), findsOneWidget);

    // Select "Quiet Solitude"
    await tester.tap(find.text('Quiet Solitude'));
    await tester.pump();

    // Type optional note
    final noteField = find.byType(TextField);
    await tester.enterText(noteField, 'Wishing you light on your journey.');
    await tester.pump();

    // Tap confirm button
    final confirmButton = find.widgetWithText(ElevatedButton, 'Pass with Grace');
    await tester.ensureVisible(confirmButton);
    await tester.tap(confirmButton);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Verify callback arguments
    expect(selectedKey, equals('grace_holding_space'));
    expect(notePassed, equals('Wishing you light on your journey.'));

    // Verify dialog dismissed
    expect(find.text('Part Ways with Grace'), findsNothing);
  });

  testWidgets(
      'Test 4: Concluded dialogue renders closed banner and disables text input field',
      (tester) async {
    const matchId = 'm_test_4';
    const peerId = 'p_test_4';

    final controller = ChatDialogueController(
      matchId: matchId,
      httpClient: httpClient,
      wsService: fakeWsService,
      currentUserId: 'current_user_1',
      initialState: const ChatDialogueState(
        isDialogueClosed: true,
        closureTemplateKey: 'grace_paths_diverge',
      ),
    );

    await tester.pumpWidget(createChatScreen(
      matchId: matchId,
      peerId: peerId,
      customController: controller,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // Verify Concluded Dialogue Banner is rendered
    expect(
      find.text('This dialogue has concluded with grace. Archived in peace.'),
      findsOneWidget,
    );
    expect(find.text('Dialogue Concluded'), findsOneWidget);

    // Verify text input bar is NOT present
    expect(find.text('Speak with mindful intention...'), findsNothing);
    expect(find.byType(TextField), findsNothing);
  });
}
