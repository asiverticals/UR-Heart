import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/ai_sanctuary/presentation/screens/eva_sanctuary_screen.dart';
import '../../features/auth/presentation/providers/auth_controller.dart';
import '../../features/auth/presentation/screens/age_gate_auth_screen.dart';
import '../../features/auth/presentation/screens/consent_screen.dart';
import '../../features/auth/presentation/screens/magic_link_screen.dart';
import '../../features/blind_date/presentation/screens/blind_date_hub_screen.dart';
import '../../features/blind_date/presentation/screens/blind_date_session_screen.dart';
import '../../features/chat/presentation/screens/chat_dialogue_screen.dart';
import '../../features/feed/domain/models/discovery_profile.dart';
import '../../features/feed/presentation/screens/ignored_profiles_screen.dart';
import '../../features/legal_vault/presentation/screens/vault_legal_screen.dart';
import '../../features/navigation/presentation/screens/sanctuary_navigation_shell.dart';
import '../../features/profile/presentation/screens/seeker_profile_detail_screen.dart';
import '../../features/profile_setup/presentation/screens/profile_setup_screen.dart';
import '../../features/rewards/presentation/screens/growth_hub_screen.dart';
import '../../features/settings/presentation/screens/app_info_screen.dart';
import '../../features/settings/presentation/screens/sanctuary_settings_screen.dart';
import '../../features/settings/presentation/screens/superadmin_kyc_desk_screen.dart';
import '../services/window_security_service.dart';
import '../storage/secure_session_storage.dart';

class _GoRouterRefreshNotifier extends ChangeNotifier {
  void notify() => notifyListeners();
}

final authStateProvider = StreamProvider<bool>((ref) {
  final storage = ref.watch(secureSessionStorageProvider);
  return storage.watchAuthenticationState();
});

final goRouterProvider = Provider<GoRouter>((ref) {
  final refreshNotifier = _GoRouterRefreshNotifier();
  ref.listen<AsyncValue<bool>>(authStateProvider, (_, __) {
    refreshNotifier.notify();
  });
  ref.onDispose(refreshNotifier.dispose);

  final router = GoRouter(
    initialLocation: '/main',
    debugLogDiagnostics: false,
    refreshListenable: refreshNotifier,
    redirect: (BuildContext context, GoRouterState state) async {
      unawaited(
        WindowSecurityService.enforceWindowProtection(state.matchedLocation),
      );

      final isAuthRoute = state.matchedLocation == '/auth' ||
          state.matchedLocation == '/consent' ||
          state.matchedLocation == '/magic-link';

      final authState = ref.read(authStateProvider);
      if (authState.isLoading) {
        if (!isAuthRoute) {
          // Keep protected routes closed while authentication state loads.
          // Defer redirect until the auth stream emits.
          try {
            final isLoggedIn = await ref
                .read(authStateProvider.future)
                .timeout(const Duration(seconds: 3), onTimeout: () => false);
            if (!isLoggedIn) {
              return '/consent';
            }
          } catch (_) {
            return '/consent';
          }
        }
        return null;
      }

      final isLoggedIn = authState.value ?? false;
      if (!isLoggedIn && !isAuthRoute) {
        return '/consent';
      }
      if (isLoggedIn && isAuthRoute) {
        return '/main';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/consent',
        builder: (context, state) => const ConsentScreen(),
      ),
      GoRoute(
        path: '/auth',
        builder: (context, state) => const AgeGateAuthScreen(),
      ),
      GoRoute(
        path: '/magic-link',
        builder: (context, state) => MagicLinkScreen(
          token: state.uri.queryParameters['token'],
        ),
      ),
      GoRoute(
        path: '/profile-setup',
        builder: (context, state) => const ProfileSetupScreen(),
      ),
      GoRoute(
        path: '/main',
        builder: (context, state) => const SanctuaryNavigationShell(),
      ),
      GoRoute(
        path: '/chat-dialogue',
        builder: (context, state) => ChatDialogueScreen(
          matchId: state.uri.queryParameters['match_id'] ??
              state.uri.queryParameters['matchId'] ??
              '',
          peerId: state.uri.queryParameters['peer_id'] ??
              state.uri.queryParameters['peerId'] ??
              '',
        ),
      ),
      GoRoute(
        path: '/blind-date',
        builder: (context, state) => const BlindDateHubScreen(),
      ),
      GoRoute(
        path: '/blind-date-session',
        builder: (context, state) => BlindDateSessionScreen(
          sessionId: state.uri.queryParameters['session_id'] ??
              state.uri.queryParameters['sessionId'] ??
              '',
        ),
      ),
      GoRoute(
        path: '/growth',
        builder: (context, state) => const GrowthHubScreen(),
      ),
      GoRoute(
        path: '/vault',
        builder: (context, state) => const VaultLegalScreen(),
      ),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SanctuarySettingsScreen(),
      ),
      GoRoute(
        path: '/admin/kyc-desk',
        redirect: (context, state) {
          final user = ref.read(currentUserProvider);
          if (user?.role != 'superadmin' && user?.role != 'moderator') {
            return '/main';
          }
          return null;
        },
        builder: (context, state) => const SuperadminKycDeskScreen(),
      ),
      GoRoute(
        path: '/app-info',
        builder: (context, state) => const AppInfoScreen(),
      ),
      GoRoute(
        path: '/seeker-detail',
        builder: (context, state) => SeekerProfileDetailScreen(
          userId: state.uri.queryParameters['user_id'] ??
              state.uri.queryParameters['userId'] ??
              '',
          initialProfile: state.extra is DiscoveryProfile
              ? state.extra as DiscoveryProfile
              : null,
        ),
      ),
      GoRoute(
        path: '/ignored-profiles',
        builder: (context, state) => const IgnoredProfilesScreen(),
      ),
      GoRoute(
        path: '/eva-sanctuary',
        builder: (context, state) => const EvaSanctuaryScreen(),
      ),
    ],
  );
  ref.onDispose(router.dispose);
  return router;
});
