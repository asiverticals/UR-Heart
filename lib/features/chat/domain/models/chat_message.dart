import 'package:flutter/foundation.dart';

/// Immutable model representing an encrypted 1:1 dialogue message.
@immutable
class ChatMessage {
  final int? id;
  final String matchId;
  final String senderId;
  final String encryptedText;
  final String status; // 'sending', 'sent', 'delivered', 'read'
  final String? clientId;
  final DateTime createdAt;

  const ChatMessage({
    this.id,
    required this.matchId,
    required this.senderId,
    required this.encryptedText,
    this.status = 'sent',
    this.clientId,
    required this.createdAt,
  });

  ChatMessage copyWith({
    int? id,
    String? matchId,
    String? senderId,
    String? encryptedText,
    String? status,
    String? clientId,
    DateTime? createdAt,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      matchId: matchId ?? this.matchId,
      senderId: senderId ?? this.senderId,
      encryptedText: encryptedText ?? this.encryptedText,
      status: status ?? this.status,
      clientId: clientId ?? this.clientId,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] is int
          ? json['id'] as int
          : (json['id'] != null ? int.tryParse(json['id'].toString()) : null),
      matchId: json['match_id']?.toString() ?? '',
      senderId: json['sender_id']?.toString() ?? '',
      encryptedText: json['encrypted_text']?.toString() ?? '',
      status: json['status']?.toString() ?? 'sent',
      clientId: json['client_id']?.toString(),
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'].toString()) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'match_id': matchId,
      'sender_id': senderId,
      'encrypted_text': encryptedText,
      'status': status,
      'client_id': clientId,
      'created_at': createdAt.toIso8601String(),
    };
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ChatMessage &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          clientId == other.clientId &&
          matchId == other.matchId &&
          senderId == other.senderId &&
          encryptedText == other.encryptedText &&
          status == other.status;

  @override
  int get hashCode =>
      id.hashCode ^
      clientId.hashCode ^
      matchId.hashCode ^
      senderId.hashCode ^
      encryptedText.hashCode ^
      status.hashCode;
}
