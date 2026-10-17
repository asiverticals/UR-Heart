import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/notification_service.dart';
import '../theme/glass_tokens.dart';
import '../theme/theme_controller.dart';
import 'app_router.dart';

class UrHeartApp extends ConsumerWidget {
  const UrHeartApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.listen<AsyncValue<bool>>(
      authStateProvider,
      (previous, next) {
        if (previous?.value != true && next.value == true) {
          ref
              .read(notificationServiceProvider)
              .initialize(fcmToken: 'sample_device_fcm_token')
              .catchError((_) => false);
        }
      },
    );

    final router = ref.watch(goRouterProvider);
    final themeState = ref.watch(themeProvider);

    return MaterialApp.router(
      title: 'UR-Heart Sanctuary',
      debugShowCheckedModeBanner: false,
      routerConfig: router,
      themeMode: themeState.isDark ? ThemeMode.dark : ThemeMode.light,
      theme: ThemeData(
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFF9F6F0),
        colorScheme: ColorScheme.fromSeed(
          seedColor: SanctuaryGlassTokens.brandPine,
          brightness: Brightness.light,
        ),
      ),
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0F1115),
        colorScheme: ColorScheme.fromSeed(
          seedColor: SanctuaryGlassTokens.brandPine,
          brightness: Brightness.dark,
        ),
      ),
    );
  }
}
