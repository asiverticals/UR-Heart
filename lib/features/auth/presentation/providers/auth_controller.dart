import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

@immutable
class CurrentUser {
  final String id;
  final String role;
  final String? email;

  const CurrentUser({
    required this.id,
    required this.role,
    this.email,
  });
}

final currentUserProvider = StateProvider<CurrentUser?>((ref) => null);
