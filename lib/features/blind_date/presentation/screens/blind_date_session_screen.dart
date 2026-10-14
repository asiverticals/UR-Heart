import 'package:flutter/material.dart';

class BlindDateSessionScreen extends StatelessWidget {
  final String sessionId;

  const BlindDateSessionScreen({
    super.key,
    required this.sessionId,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Text('BlindDateSessionScreen (sessionId: $sessionId)'),
      ),
    );
  }
}
