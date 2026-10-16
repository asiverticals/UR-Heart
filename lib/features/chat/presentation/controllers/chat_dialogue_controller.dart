import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';
import '../../../auth/presentation/controllers/auth_controller.dart';
import '../../data/chat_websocket_service.dart';
import '../../domain/models/chat_message.dart';

@immutable
class ChatDialogueState {
  final List<ChatMessage> messages;
  final bool isPeerOnline;
  final bool isPeerTyping;
  final bool isDialogueClosed;
  final String? closureTemplateKey;
  final bool isSending;
  final bool isLoadingHistory;
  final String? errorMessage;

  const ChatDialogueState({
    this.messages = const [],
    this.isPeerOnline = false,
    this.isPeerTyping = false,
    this.isDialogueClosed = false,
    this.closureTemplateKey,
    this.isSending = false,
    this.isLoadingHistory = false,
    this.errorMessage,
  });

  ChatDialogueState copyWith({
    List<ChatMessage>? messages,
    bool? isPeerOnline,
    bool? isPeerTyping,
    bool? isDialogueClosed,
    String? closureTemplateKey,
    bool? isSending,
    bool? isLoadingHistory,
    String? errorMessage,
  }) {
    return ChatDialogueState(
      messages: messages ?? this.messages,
      isPeerOnline: isPeerOnline ?? this.isPeerOnline,
      isPeerTyping: isPeerTyping ?? this.isPeerTyping,
      isDialogueClosed: isDialogueClosed ?? this.isDialogueClosed,
      closureTemplateKey: closureTemplateKey ?? this.closureTemplateKey,
      isSending: isSending ?? this.isSending,
      isLoadingHistory: isLoadingHistory ?? this.isLoadingHistory,
      errorMessage: errorMessage,
    );
  }
}

final chatDialogueControllerProvider = StateNotifierProvider.autoDispose.family<
    ChatDialogueController, ChatDialogueState, String>((ref, matchId) {
  final httpClient = ref.watch(sanctuaryHttpClientProvider);
  final wsService = ref.watch(chatWebSocketServiceProvider);
  final currentUser = ref.watch(currentUserProvider);

  final controller = ChatDialogueController(
    matchId: matchId,
    httpClient: httpClient,
    wsService: wsService,
    currentUserId: currentUser?.id ?? '',
  );
  return controller;
});

class ChatDialogueController extends StateNotifier<ChatDialogueState> {
  final String matchId;
  final SanctuaryHttpClient _httpClient;
  final ChatWebSocketService _wsService;
  final String currentUserId;

  String _peerId = '';
  StreamSubscription<Map<String, dynamic>>? _eventSubscription;
  Timer? _typingResetTimer;

  ChatDialogueController({
    required this.matchId,
    required SanctuaryHttpClient httpClient,
    required ChatWebSocketService wsService,
    required this.currentUserId,
    ChatDialogueState initialState = const ChatDialogueState(),
  })  : _httpClient = httpClient,
        _wsService = wsService,
        super(initialState);

  String get peerId => _peerId;

  /// Initializes the dialogue: loads historical messages and binds WebSocket stream.
  Future<void> initializeDialogue(String matchId, String peerId) async {
    _peerId = peerId;

    // 1. Subscribe to real-time events
    _eventSubscription?.cancel();
    _eventSubscription = _wsService.eventStream.listen(_handleSocketFrame);

    // 2. Ensure WebSocket is connected before dispatching read receipts
    if (!_wsService.isConnected) {
      await _wsService.connect();
    }

    // 3. Fetch history from backend and sync read status
    await _syncHistoryAndReadStatus(showLoading: true);
  }

  Future<void> _syncHistoryAndReadStatus({bool showLoading = false}) async {
    if (showLoading && state.messages.isEmpty && mounted) {
      state = state.copyWith(isLoadingHistory: true, errorMessage: null);
    }

    try {
      final res = await _httpClient.get('/api/v1/chat/messages/$matchId');
      final dataList = res['data'] as List<dynamic>? ?? const [];
      final historical = dataList
          .map((m) => ChatMessage.fromJson(m as Map<String, dynamic>))
          .toList();

      final meta = res['meta'] as Map<String, dynamic>?;
      final bool isActive = meta?['is_active'] ?? true;
      final String? closureKey = meta?['closure_template_key']?.toString();
      final bool isClosed = !isActive || (meta?['closure_status'] == 'closed');

      if (mounted) {
        final serverClientIds = historical
            .map((m) => m.clientId)
            .whereType<String>()
            .toSet();
        final pendingLocal = state.messages.where((m) =>
            m.id == null &&
            m.clientId != null &&
            !serverClientIds.contains(m.clientId));

        state = state.copyWith(
          messages: historical.isNotEmpty
              ? [...historical, ...pendingLocal]
              : state.messages,
          isLoadingHistory: false,
          isDialogueClosed: isClosed || state.isDialogueClosed,
          closureTemplateKey: closureKey ?? state.closureTemplateKey,
        );
      }

      // Mark unread messages as read only when connected and dialogue active
      if (_peerId.isNotEmpty && _wsService.isConnected && !isClosed) {
        _wsService.sendReadReceipt(matchId: matchId, recipientId: _peerId);
      }
    } catch (e) {
      if (mounted) {
        state = state.copyWith(
          isLoadingHistory: false,
          errorMessage: e.toString(),
        );
      }
    }
  }

  void _handleSocketFrame(Map<String, dynamic> frame) async {
    if (!mounted) return;
    final type = frame['type']?.toString();
    final frameMatchId = frame['match_id']?.toString();

    // Check if frame belongs to this dialogue
    if (frameMatchId != null && frameMatchId != matchId) {
      return;
    }

    switch (type) {
      case 'message':
        final senderId = frame['sender_id']?.toString() ?? '';
        final clientId = frame['client_id']?.toString();
        final incoming = ChatMessage.fromJson(frame);

        // Check for matching optimistic message
        final existingIdx = clientId != null
            ? state.messages.indexWhere((m) => m.clientId == clientId)
            : -1;

        if (existingIdx != -1) {
          final updated = List<ChatMessage>.from(state.messages);
          updated[existingIdx] = incoming.copyWith(status: 'delivered');
          state = state.copyWith(messages: updated);
        } else {
          // If message is from peer, send read receipt
          if (senderId != currentUserId && _peerId.isNotEmpty) {
            _wsService.sendReadReceipt(matchId: matchId, recipientId: _peerId);
          }
          state = state.copyWith(messages: [...state.messages, incoming]);
        }
        break;

      case 'ack':
        final clientId = frame['client_id']?.toString();
        final serverId = frame['id'] is int ? frame['id'] as int : null;
        final ackStatus = frame['status']?.toString() ?? 'delivered';

        if (clientId != null) {
          final updated = state.messages.map((m) {
            if (m.clientId == clientId) {
              return m.copyWith(id: serverId ?? m.id, status: ackStatus);
            }
            return m;
          }).toList();
          state = state.copyWith(messages: updated);
        }
        break;

      case 'typing':
        final senderId = frame['sender_id']?.toString();
        final isTyping = frame['is_typing'] == true;

        if (senderId != currentUserId) {
          state = state.copyWith(isPeerTyping: isTyping);
          if (isTyping) {
            _typingResetTimer?.cancel();
            _typingResetTimer = Timer(const Duration(seconds: 4), () {
              if (mounted) state = state.copyWith(isPeerTyping: false);
            });
          }
        }
        break;

      case 'read_receipt':
        // Peer has read our messages
        final updated = state.messages.map((m) {
          if (m.senderId == currentUserId && m.status != 'read') {
            return m.copyWith(status: 'read');
          }
          return m;
        }).toList();
        state = state.copyWith(messages: updated);
        break;

      case 'dialogue_closed':
        final templateKey = frame['template_key']?.toString();
        state = state.copyWith(
          isDialogueClosed: true,
          closureTemplateKey: templateKey,
          isPeerTyping: false,
        );
        break;

      case '_reconnected':
        await _syncHistoryAndReadStatus(showLoading: false);
        break;

      case 'error':
        final errorCode = frame['error_code']?.toString();
        final clientId = frame['client_id']?.toString();
        final message = frame['message']?.toString();

        if (errorCode == 'MATCH_NOT_FOUND_OR_INACTIVE' && frameMatchId == matchId) {
          state = state.copyWith(isDialogueClosed: true);
        }

        if (clientId != null) {
          final updated = state.messages.map((m) {
            if (m.clientId == clientId) {
              return m.copyWith(status: 'failed');
            }
            return m;
          }).toList();
          state = state.copyWith(messages: updated, errorMessage: message);
        }
        break;
    }
  }

  /// Dispatches encrypted/sanctuary text message to peer over secure TLS/WSS transport.
  /// Note: Transport layer is protected via WSS and authenticated 60s ticket handshake;
  /// application payload field is designated `encryptedText` for future client-side cipher integration.
  Future<void> sendTextMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || trimmed.length > 4096) return;
    if (state.isDialogueClosed) return;

    final clientId = 'c_${DateTime.now().microsecondsSinceEpoch}_${Random().nextInt(999999)}';

    final optimistic = ChatMessage(
      matchId: matchId,
      senderId: currentUserId,
      encryptedText: trimmed,
      status: 'sending',
      clientId: clientId,
      createdAt: DateTime.now(),
    );

    state = state.copyWith(
      messages: [...state.messages, optimistic],
      isSending: true,
      errorMessage: null,
    );

    try {
      _wsService.sendMessage(
        matchId: matchId,
        recipientId: _peerId,
        encryptedText: trimmed,
        clientId: clientId,
      );
    } catch (e) {
      final updated = state.messages.map((m) {
        if (m.clientId == clientId) {
          return m.copyWith(status: 'failed');
        }
        return m;
      }).toList();
      state = state.copyWith(messages: updated, errorMessage: e.toString());
    } finally {
      if (mounted) state = state.copyWith(isSending: false);
    }
  }

  /// Sends typing state indicator.
  void sendTyping(bool isTyping) {
    if (state.isDialogueClosed || _peerId.isEmpty) return;
    _wsService.sendTyping(
      matchId: matchId,
      recipientId: _peerId,
      isTyping: isTyping,
    );
  }

  /// Executes mindful "Pass with Grace" closure protocol.
  Future<bool> closeWithGrace(String templateKey, String? note) async {
    try {
      final res = await _httpClient.post(
        '/api/v1/chat/close-with-grace',
        body: {
          'match_id': matchId,
          'closure_template_key': templateKey,
          'closure_note': note,
        },
      );

      final success = res['data']?['success'] == true;
      if (success && mounted) {
        state = state.copyWith(
          isDialogueClosed: true,
          closureTemplateKey: templateKey,
          isPeerTyping: false,
        );
      }
      return success;
    } catch (e) {
      if (mounted) {
        state = state.copyWith(errorMessage: e.toString());
      }
      return false;
    }
  }

  /// Blocks the dialogue peer and severs active chat connection (Issue #7).
  Future<bool> blockPeer(String peerId, {String? reason}) async {
    try {
      final res = await _httpClient.post(
        '/api/v1/users/$peerId/block',
        body: reason != null ? {'reason': reason} : null,
      );

      final success = res['data']?['blocked'] == true || res['blocked'] == true;
      if (success && mounted) {
        state = state.copyWith(
          isDialogueClosed: true,
          closureTemplateKey: 'blocked',
          isPeerTyping: false,
        );
      }
      return success;
    } catch (e) {
      if (mounted) {
        state = state.copyWith(errorMessage: e.toString());
      }
      return false;
    }
  }

  @override
  void dispose() {
    _eventSubscription?.cancel();
    _typingResetTimer?.cancel();
    super.dispose();
  }
}
