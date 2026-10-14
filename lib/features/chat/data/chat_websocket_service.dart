import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../../core/network/sanctuary_http_client.dart';

typedef WebSocketChannelFactory = WebSocketChannel Function(Uri uri);

final chatWebSocketServiceProvider = Provider<ChatWebSocketService>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  final service = ChatWebSocketService(client);
  ref.onDispose(() => service.dispose());
  return service;
});

/// Manages real-time WebSocket communication over single-use ephemeral ticket handshake.
class ChatWebSocketService {
  final SanctuaryHttpClient _httpClient;
  final WebSocketChannelFactory _channelFactory;

  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  final _eventStreamController = StreamController<Map<String, dynamic>>.broadcast();

  bool _isManuallyClosed = false;
  bool _isConnecting = false;
  int _reconnectAttempts = 0;
  Timer? _reconnectTimer;

  static const int maxReconnectAttempts = 5;

  ChatWebSocketService(
    this._httpClient, {
    WebSocketChannelFactory? channelFactory,
  }) : _channelFactory = channelFactory ?? ((uri) => WebSocketChannel.connect(uri));

  Stream<Map<String, dynamic>> get eventStream => _eventStreamController.stream;
  bool get isConnected => _channel != null && !_isManuallyClosed;

  /// Acquires an ephemeral single-use ticket and initiates WebSocket handshake.
  Future<void> connect({String? customTicket}) async {
    if (_isConnecting) return;
    _isConnecting = true;
    _isManuallyClosed = false;

    try {
      String ticket;
      String wsUrl = 'wss://urheart.app/ws/chat';

      if (customTicket != null && customTicket.isNotEmpty) {
        ticket = customTicket;
      } else {
        final ticketResponse = await _httpClient.post('/api/v1/chat/ws-ticket');
        final data = ticketResponse['data'] as Map<String, dynamic>? ?? ticketResponse;
        ticket = data['ticket']?.toString() ?? '';
        final serverWsUrl = data['ws_url']?.toString();
        if (serverWsUrl != null && serverWsUrl.isNotEmpty) {
          wsUrl = serverWsUrl;
        }
      }

      if (ticket.isEmpty) {
        throw Exception('Failed to obtain ephemeral WebSocket ticket.');
      }

      final uri = Uri.parse('$wsUrl?ticket=$ticket');
      _channel = _channelFactory(uri);
      await _channel!.ready;

      _subscription = _channel!.stream.listen(
        _onMessageReceived,
        onError: _onError,
        onDone: _onDone,
        cancelOnError: true,
      );

      _reconnectAttempts = 0;
      debugPrint('[ChatWS] Connected successfully via ephemeral ticket handshake.');
    } catch (e) {
      debugPrint('[ChatWS] Handshake failed: $e');
      _handleDisconnectAndScheduleReconnect();
    } finally {
      _isConnecting = false;
    }
  }

  void _onMessageReceived(dynamic event) {
    try {
      Map<String, dynamic> parsed;
      if (event is String) {
        parsed = jsonDecode(event) as Map<String, dynamic>;
      } else if (event is Map<String, dynamic>) {
        parsed = event;
      } else {
        return;
      }
      _eventStreamController.add(parsed);
    } catch (e) {
      debugPrint('[ChatWS] Parse error: $e');
    }
  }

  void _onError(dynamic error) {
    debugPrint('[ChatWS] Socket stream error: $error');
    _handleDisconnectAndScheduleReconnect();
  }

  void _onDone() {
    debugPrint('[ChatWS] Socket connection closed.');
    _handleDisconnectAndScheduleReconnect();
  }

  void _handleDisconnectAndScheduleReconnect() {
    _cleanupChannel();
    if (_isManuallyClosed) return;

    if (_reconnectAttempts < maxReconnectAttempts) {
      _reconnectAttempts++;
      // Exponential backoff: 1s, 2s, 4s, 8s, 16s with jitter
      final delaySeconds = pow(2, _reconnectAttempts - 1).toInt();
      final jitterMs = Random().nextInt(500);
      final delay = Duration(seconds: delaySeconds, milliseconds: jitterMs);

      debugPrint('[ChatWS] Scheduling reconnect #$_reconnectAttempts in ${delay.inSeconds}s...');
      _reconnectTimer?.cancel();
      _reconnectTimer = Timer(delay, () => connect());
    } else {
      debugPrint('[ChatWS] Max reconnection attempts reached.');
    }
  }

  /// Sends text message frame over WebSocket.
  void sendMessage({
    required String matchId,
    required String recipientId,
    required String encryptedText,
    required String clientId,
  }) {
    _sendFrame({
      'type': 'message',
      'match_id': matchId,
      'recipient_id': recipientId,
      'encrypted_text': encryptedText,
      'client_id': clientId,
    });
  }

  /// Sends typing state indicator frame.
  void sendTyping({
    required String matchId,
    required String recipientId,
    required bool isTyping,
  }) {
    try {
      _sendFrame({
        'type': 'typing',
        'match_id': matchId,
        'recipient_id': recipientId,
        'is_typing': isTyping,
      });
    } catch (e) {
      debugPrint('[ChatWS] Failed to send typing indicator: $e');
    }
  }

  /// Sends read receipt confirmation frame.
  void sendReadReceipt({
    required String matchId,
    required String recipientId,
  }) {
    try {
      _sendFrame({
        'type': 'read_receipt',
        'match_id': matchId,
        'recipient_id': recipientId,
      });
    } catch (e) {
      debugPrint('[ChatWS] Failed to send read receipt: $e');
    }
  }

  void _sendFrame(Map<String, dynamic> frame) {
    final channel = _channel;
    if (channel == null) {
      throw StateError('WebSocket is not connected.');
    }
    channel.sink.add(jsonEncode(frame));
  }

  void _cleanupChannel() {
    _subscription?.cancel();
    _subscription = null;
    _channel?.sink.close();
    _channel = null;
  }

  /// Closes the connection and suppresses auto-reconnection.
  void disconnect() {
    _isManuallyClosed = true;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _cleanupChannel();
  }

  void dispose() {
    disconnect();
    _eventStreamController.close();
  }
}
