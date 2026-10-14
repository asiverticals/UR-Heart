import 'package:flutter/material.dart';

class SeekerProfileDetailScreen extends StatelessWidget {
  final String userId;

  const SeekerProfileDetailScreen({
    super.key,
    required this.userId,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Text('SeekerProfileDetailScreen (userId: $userId)'),
      ),
    );
  }
}
