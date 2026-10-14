import 'package:flutter/material.dart';

class ChatDialogueScreen extends StatelessWidget {
  final String matchId;
  final String peerId;

  const ChatDialogueScreen({
    super.key,
    required this.matchId,
    required this.peerId,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Text('ChatDialogueScreen (matchId: $matchId, peerId: $peerId)'),
      ),
    );
  }
}
