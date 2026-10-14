import 'package:flutter/material.dart';

class MagicLinkScreen extends StatelessWidget {
  final String? token;

  const MagicLinkScreen({super.key, this.token});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Text('MagicLinkScreen'),
      ),
    );
  }
}
