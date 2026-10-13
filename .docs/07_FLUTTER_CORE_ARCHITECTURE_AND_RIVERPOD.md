1. Client Topology & Modular Slicing Invariants
UR-Heart Sanctuary's client is engineered on Flutter 3.10+ targeting Native Android (.apk/.aab) and installable iOS/Desktop PWA with 100% codebase symmetry. The architecture strictly adheres to compile-time Dart null-safety, immutable state models (@immutable), and feature-driven vertical slices.
MD

+ 1

lib/
├── core/
│   ├── app/                              # Root application bootstrap & lifecycle
│   │   ├── app_router.dart               # GoRouter with reactive auth redirects
│   │   └── ur_heart_app.dart             # MaterialApp.router with Riverpod binding
│   ├── constants/                        # app_typography.dart, layout metrics
│   ├── network/                          # HTTP client, auth interceptor, retry logic
│   ├── services/                         # Notification, window security, platform channels
│   ├── storage/                          # Keystore EncryptedSharedPreferences vault
│   └── theme/                            # glass_tokens.dart, theme_controller.dart
└── features/
    └── <feature_name>/                   # Isolated domain slices
        ├── data/                         # Remote data sources, API client calls, DTOs
        ├── domain/                       # Pure Dart entities, immutable state records
        ├── controllers/                  # Riverpod StateNotifier / AsyncNotifier
        └── presentation/                 # Glassmorphic screens, frosted components

MD

Non-Negotiable Frontend Rules
Zero StatefulWidgets for Business Logic: Presentation widgets must extend ConsumerWidget or ConsumerStatefulWidget. All state mutation is handled inside Riverpod StateNotifier controllers.
MD

Immutable State Transitions: State classes must be annotated with @immutable and use copyWith patterns. Direct field mutation is prohibited.
MD

Hardware Keystore Exclusivity: Sensitive session tokens (ur_heart_auth_token, user_role) must be written exclusively to Android Keystore-backed encrypted storage, never to plain SharedPreferences.
MD

Permanent Window Security: WindowSecurityService.isBypassedUser() is hardcoded to permanently return false; to prohibit administrative inspection of veiled or encrypted viewports.
MD

1. Application Bootstrap, Routing & Auth Guards
The application uses go_router backed by Riverpod state streams to handle authentication guards, deep linking, and PWA URL synchronization.
MD

Dart

// lib/core/app/app_router.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/presentation/screens/consent_screen.dart';
import '../../features/auth/presentation/screens/age_gate_auth_screen.dart';
import '../../features/auth/presentation/screens/magic_link_screen.dart';
import '../../features/auth/presentation/providers/auth_controller.dart';
import '../../features/profile_setup/presentation/screens/profile_setup_screen.dart';
import '../../features/navigation/presentation/screens/sanctuary_navigation_shell.dart';
import '../../features/chat/presentation/screens/chat_dialogue_screen.dart';
import '../../features/blind_date/presentation/screens/blind_date_hub_screen.dart';
import '../../features/blind_date/presentation/screens/blind_date_session_screen.dart';
import '../../features/rewards/presentation/screens/growth_hub_screen.dart';
import '../../features/legal_vault/presentation/screens/vault_legal_screen.dart';
import '../../features/settings/presentation/screens/sanctuary_settings_screen.dart';
import '../../features/settings/presentation/screens/superadmin_kyc_desk_screen.dart';
import '../../features/settings/presentation/screens/app_info_screen.dart';
import '../../features/profile/presentation/screens/seeker_profile_detail_screen.dart';
import '../../features/feed/presentation/screens/ignored_profiles_screen.dart';
import '../../features/ai_sanctuary/presentation/screens/eva_sanctuary_screen.dart';
import '../storage/secure_session_storage.dart';

final authStateProvider = StreamProvider<bool>((ref) {
  final storage = ref.watch(secureSessionStorageProvider);
  return storage.watchAuthenticationState();
});

final goRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);

  return GoRouter(
    initialLocation: '/main',
    debugLogDiagnostics: false,
    redirect: (BuildContext context, GoRouterState state) async {
      final isLoggedIn = authState.value ?? false;
      final isAuthRoute = state.matchedLocation == '/auth' ||
          state.matchedLocation == '/consent' ||
          state.matchedLocation == '/magic-link';

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
          matchId: state.uri.queryParameters['match_id'] ?? '',
          peerId: state.uri.queryParameters['peer_id'] ?? '',
        ),
      ),
      GoRoute(
        path: '/blind-date',
        builder: (context, state) => const BlindDateHubScreen(),
      ),
      GoRoute(
        path: '/blind-date-session',
        builder: (context, state) => BlindDateSessionScreen(
          sessionId: state.uri.queryParameters['session_id'] ?? '',
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
          userId: state.uri.queryParameters['user_id'] ?? '',
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
});

MD

Root Application Entry Point (lib/core/app/ur_heart_app.dart)
Dart

// lib/core/app/ur_heart_app.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app_router.dart';
import '../theme/theme_controller.dart';
import '../theme/glass_tokens.dart';

class UrHeartApp extends ConsumerWidget {
  const UrHeartApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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

MD

1. Hardware Security & Session Isolation Vault
3.1 Hardware Anti-Screen Capture (FLAG_SECURE = 8192)
Enforced via native Kotlin MethodChannel in android/app/src/main/kotlin/com/urheart/app/MainActivity.kt and managed in Dart by WindowSecurityService.
MD

Kotlin

// android/app/src/main/kotlin/com/urheart/app/MainActivity.kt
package com.urheart.app

import android.os.Bundle
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity: FlutterActivity() {
    private val CHANNEL = "com.urheart.app/window_security"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "enableSecureWindow" -> {
                    window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
                    result.success(true)
                }
                "disableSecureWindow" -> {
                    window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }
    }
}

MD

Dart

// lib/core/services/window_security_service.dart
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

class WindowSecurityService {
  static const MethodChannel _channel = MethodChannel('com.urheart.app/window_security');

  /// Strict non-negotiable invariant: administrative bypass is permanently disabled
  static bool isBypassedUser() {
    return false;
  }

  /// Sets hardware FLAG_SECURE on Android. (Note: On Web/PWA, browser window protection enforces watermarks & user-select: none since hardware shortcuts cannot be intercepted in sandboxed browsers)
  static Future<void> enforceWindowProtection(String currentRoute) async {
    if (isBypassedUser()) return;

    final sensitiveRoutes = {
      '/chat-dialogue',
      '/main',
      '/seeker-detail',
      '/blind-date-session',
      '/vault',
    };

    if (sensitiveRoutes.contains(currentRoute)) {
      if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
        try {
          await _channel.invokeMethod('enableSecureWindow');
        } catch (_) {}
      }
    }
  }

  static Future<void> relaxWindowProtection() async {
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      try {
        await _channel.invokeMethod('disableSecureWindow');
      } catch (_) {}
    }
  }
}

MD

3.2 Android Keystore Vault (SecureSessionStorage)
Stores JWTs, roles, and cryptographic materials backed by AES-256 GCM in the Android Keystore system.
MD

Dart

// lib/core/storage/secure_session_storage.dart
import 'dart:async';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final secureSessionStorageProvider = Provider<SecureSessionStorage>((ref) {
  return SecureSessionStorage();
});

class SecureSessionStorage {
  static const _tokenKey = 'ur_heart_auth_token';
  static const _refreshTokenKey = 'ur_heart_refresh_token';
  static const _roleKey = 'ur_heart_user_role';
  static const _userIdKey = 'ur_heart_user_id';

  final FlutterSecureStorage _vault = const FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
      resetOnError: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
    ),
  );

  final StreamController<bool> _authStreamController = StreamController<bool>.broadcast();

  Stream<bool> watchAuthenticationState() async*{
    final initialToken = await readAuthToken();
    yield initialToken != null && initialToken.isNotEmpty;
    yield* _authStreamController.stream;
  }

  Future<void> persistSession({
    required String accessToken,
    required String refreshToken,
    required String userId,
    required String role,
  }) async {
    await _vault.write(key:_tokenKey, value: accessToken);
    await _vault.write(key:_refreshTokenKey, value: refreshToken);
    await _vault.write(key:_userIdKey, value: userId);
    await _vault.write(key:_roleKey, value: role);
    _authStreamController.add(true);
  }

  Future<String?> readAuthToken() => _vault.read(key:_tokenKey);
  Future<void> saveAuthToken(String token) => _vault.write(key:_tokenKey, value: token);
  Future<String?> readRefreshToken() => _vault.read(key:_refreshTokenKey);
  Future<String?> readUserId() => _vault.read(key:_userIdKey);
  Future<String?> readUserRole() => _vault.read(key:_roleKey);

  Future<void> clearSession() async {
    await _vault.deleteAll();
    _authStreamController.add(false);
  }
}

MD

1. Riverpod State Management System & Core Controllers
State management relies on Riverpod 2.x StateNotifier classes coupled with immutable Dart state records.
MD

┌────────────────────────────────────────────────────────────────────────┐
│                   RIVERPOD STATE MANAGEMENT LIFECYCLE                  │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Immutable State Record (@immutable, copyWith)                       │
│ 2. StateNotifier Controller (Dispatches mutations & network requests)  │
│ 3. StateNotifierProvider (Exposes state to ConsumerWidgets)            │
│ 4. UI Layer: ref.watch() for rendering, ref.read() for user actions   │
└────────────────────────────────────────────────────────────────────────┘

MD

4.1 Theme Controller (themeProvider)
Dart

// lib/core/theme/theme_controller.dart
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

@immutable
class ThemeState {
  final bool isDark;
  const ThemeState({required this.isDark});

  ThemeState copyWith({bool? isDark}) {
    return ThemeState(isDark: isDark ?? this.isDark);
  }
}

class ThemeController extends StateNotifier<ThemeState> {
  static const _prefKey = 'sanctuary_theme_dark_mode';

  ThemeController() : super(const ThemeState(isDark: true)) {
    _loadPreference();
  }

  Future<void> _loadPreference() async {
    final prefs = await SharedPreferences.getInstance();
    final isDark = prefs.getBool(_prefKey) ?? true;
    state = ThemeState(isDark: isDark);
  }

  Future<void> toggleTheme() async {
    final nextMode = !state.isDark;
    state = state.copyWith(isDark: nextMode);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_prefKey, nextMode);
  }
}

final themeProvider = StateNotifierProvider<ThemeController, ThemeState>((ref) {
  return ThemeController();
});

MD

4.2 Navigation Index Provider (navigationIndexProvider)
Dart

// lib/features/navigation/presentation/controllers/navigation_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

final navigationIndexProvider = StateProvider<int>((ref) => 0);

MD

4.3 Growth Hub Controller (growthHubControllerProvider)
Manages rewarded ads, sleep multipliers, and micro-perk balance updates.
MD

Dart

// lib/features/growth/presentation/controllers/growth_hub_controller.dart
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/billing/sanctuary_billing_service.dart';

@immutable
class GrowthHubState {
  final int rewardBalance;
  final int streakCount;
  final double restMultiplier;
  final bool isNightSlumberActive;
  final bool isLoading;
  final String? errorMessage;

  const GrowthHubState({
    required this.rewardBalance,
    required this.streakCount,
    required this.restMultiplier,
    required this.isNightSlumberActive,
    this.isLoading = false,
    this.errorMessage,
  });

  GrowthHubState copyWith({
    int? rewardBalance,
    int? streakCount,
    double? restMultiplier,
    bool? isNightSlumberActive,
    bool? isLoading,
    String? errorMessage,
  }) {
    return GrowthHubState(
      rewardBalance: rewardBalance ?? this.rewardBalance,
      streakCount: streakCount ?? this.streakCount,
      restMultiplier: restMultiplier ?? this.restMultiplier,
      isNightSlumberActive: isNightSlumberActive ?? this.isNightSlumberActive,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
    );
  }
}

class GrowthHubController extends StateNotifier<GrowthHubState> {
  final SanctuaryBillingService _billingService;

  GrowthHubController(this._billingService)
      : super(const GrowthHubState(
          rewardBalance: 0,
          streakCount: 0,
          restMultiplier: 1.0,
          isNightSlumberActive: false,
        ));

  Future<void> claimAdReward({
    required String transactionId,
    required String adType,
    required String network,
  }) async {
    state = state.copyWith(isLoading: true, errorMessage: null);
    try {
      final result = await _billingService.claimReward(
        transactionId: transactionId,
        adType: adType,
        network: network,
      );
      state = state.copyWith(
        rewardBalance: result['new_balance'] as int,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, errorMessage: e.toString());
    }
  }

  void updateSlumberMultiplier(double multiplier) {
    state = state.copyWith(
      restMultiplier: multiplier,
      isNightSlumberActive: multiplier > 1.0,
    );
  }
}

final growthHubControllerProvider =
    StateNotifierProvider<GrowthHubController, GrowthHubState>((ref) {
  final billingService = ref.watch(sanctuaryBillingServiceProvider);
  return GrowthHubController(billingService);
});

MD

4.4 Resonances Controller (resonancesControllerProvider)
Dart

// lib/features/resonances/presentation/controllers/resonances_controller.dart
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';

@immutable
class ResonancesState {
  final List<dynamic> incomingLikes;
  final List<dynamic> mutualMatches;
  final bool isLoading;
  final String? error;

  const ResonancesState({
    this.incomingLikes = const [],
    this.mutualMatches = const [],
    this.isLoading = false,
    this.error,
  });

  ResonancesState copyWith({
    List<dynamic>? incomingLikes,
    List<dynamic>? mutualMatches,
    bool? isLoading,
    String? error,
  }) {
    return ResonancesState(
      incomingLikes: incomingLikes ?? this.incomingLikes,
      mutualMatches: mutualMatches ?? this.mutualMatches,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

class ResonancesController extends StateNotifier<ResonancesState> {
  final SanctuaryHttpClient _client;

  ResonancesController(this._client) : super(const ResonancesState()) {
    fetchResonances();
  }

  Future<void> fetchResonances() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final incoming = await _client.get('/api/v1/resonances/incoming');
      final mutual = await _client.get('/api/v1/resonances/mutual');
      state = state.copyWith(
        incomingLikes: incoming['data'] ?? [],
        mutualMatches: mutual['data'] ?? [],
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

final resonancesControllerProvider =
    StateNotifierProvider<ResonancesController, ResonancesState>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return ResonancesController(client);
});

MD

4.5 Blind Date Controller (blindDateControllerProvider)
Enforces Condition C1 1M MAU gate and anonymous timer handshake.
MD

Dart

// lib/features/blind_date/presentation/controllers/blind_date_controller.dart
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';

@immutable
class BlindDateState {
  final bool isMilestoneLocked;
  final int currentMau;
  final int targetMau;
  final String queueStatus; // 'idle', 'waiting', 'paired'
  final String? activeSessionId;
  final int remainingSeconds;
  final bool isLoading;

  const BlindDateState({
    this.isMilestoneLocked = true,
    this.currentMau = 0,
    this.targetMau = 1000000,
    this.queueStatus = 'idle',
    this.activeSessionId,
    this.remainingSeconds = 180,
    this.isLoading = false,
  });

  BlindDateState copyWith({
    bool? isMilestoneLocked,
    int? currentMau,
    int? targetMau,
    String? queueStatus,
    String? activeSessionId,
    int? remainingSeconds,
    bool? isLoading,
  }) {
    return BlindDateState(
      isMilestoneLocked: isMilestoneLocked ?? this.isMilestoneLocked,
      currentMau: currentMau ?? this.currentMau,
      targetMau: targetMau ?? this.targetMau,
      queueStatus: queueStatus ?? this.queueStatus,
      activeSessionId: activeSessionId ?? this.activeSessionId,
      remainingSeconds: remainingSeconds ?? this.remainingSeconds,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class BlindDateController extends StateNotifier<BlindDateState> {
  final SanctuaryHttpClient _client;

  BlindDateController(this._client) : super(const BlindDateState()) {
    checkMilestoneStatus();
  }

  Future<void> checkMilestoneStatus() async {
    try {
      final res = await _client.get('/api/v1/blind-date/eligibility');
      final data = res['data'];
      state = state.copyWith(
        isMilestoneLocked: data['status'] == 'milestone_locked',
        currentMau: data['current_mau'] ?? 0,
        targetMau: data['target_mau'] ?? 1000000,
      );
    } catch (_) {}
  }

  Future<void> joinQueue() async {
    state = state.copyWith(isLoading: true);
    try {
      final res = await _client.post('/api/v1/blind-date/queue/join', body: {});
      state = state.copyWith(
        queueStatus: 'waiting',
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false);
    }
  }
}

final blindDateControllerProvider =
    StateNotifierProvider<BlindDateController, BlindDateState>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return BlindDateController(client);
});

MD

4.6 Vault Controller (vaultControllerProvider)
Dart

// lib/features/legal_vault/presentation/controllers/vault_controller.dart
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/sanctuary_http_client.dart';

@immutable
class VaultState {
  final List<dynamic> grievances;
  final Map<String, dynamic>? nominee;
  final bool isExportPending;
  final bool isLoading;

  const VaultState({
    this.grievances = const [],
    this.nominee,
    this.isExportPending = false,
    this.isLoading = false,
  });

  VaultState copyWith({
    List<dynamic>? grievances,
    Map<String, dynamic>? nominee,
    bool? isExportPending,
    bool? isLoading,
  }) {
    return VaultState(
      grievances: grievances ?? this.grievances,
      nominee: nominee ?? this.nominee,
      isExportPending: isExportPending ?? this.isExportPending,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class VaultController extends StateNotifier<VaultState> {
  final SanctuaryHttpClient _client;

  VaultController(this._client) : super(const VaultState()) {
    loadVaultData();
  }

  Future<void> loadVaultData() async {
    state = state.copyWith(isLoading: true);
    try {
      final grv = await _client.get('/api/v1/vault/grievances');
      final nom = await _client.get('/api/v1/vault/nominee');
      state = state.copyWith(
        grievances: grv['data'] ?? [],
        nominee: nom['data'],
        isLoading: false,
      );
    } catch (_) {
      state = state.copyWith(isLoading: false);
    }
  }
}

final vaultControllerProvider =
    StateNotifierProvider<VaultController, VaultState>((ref) {
  final client = ref.watch(sanctuaryHttpClientProvider);
  return VaultController(client);
});

MD

1. Base Networking Pipeline & Error Translators
Implemented via SanctuaryHttpClient with automatic JWT Bearer injection, refresh cycles, and standardized error encapsulation.
MD

Dart

// lib/core/network/sanctuary_http_client.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../storage/secure_session_storage.dart';

final sanctuaryHttpClientProvider = Provider<SanctuaryHttpClient>((ref) {
  final storage = ref.watch(secureSessionStorageProvider);
  return SanctuaryHttpClient(storage);
});

class SanctuaryHttpClient {
  static const String baseUrl = 'https://urheart.app';
  final SecureSessionStorage _storage;

  SanctuaryHttpClient(this._storage);

  Future<Map<String, dynamic>> get(String path) async {
    return _sendRequest('GET', path);
  }

  Future<Map<String, dynamic>> post(String path, {Map<String, dynamic>? body}) async {
    return _sendRequest('POST', path, body: body);
  }

  Future<Map<String, dynamic>> delete(String path, {Map<String, dynamic>? body}) async {
    return _sendRequest('DELETE', path, body: body);
  }

  Future<Map<String, dynamic>> _sendRequest(
    String method,
    String path, {
    Map<String, dynamic>? body,
    bool isRetry = false,
  }) async {
    final token = await _storage.readAuthToken();
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };

    final uri = Uri.parse('$baseUrl$path');
    http.Response response;

    switch (method) {
      case 'GET':
        response = await http.get(uri, headers: headers);
        break;
      case 'POST':
        response = await http.post(uri, headers: headers, body: jsonEncode(body ?? {}));
        break;
      case 'DELETE':
        response = await http.delete(uri, headers: headers, body: jsonEncode(body ?? {}));
        break;
      default:
        throw UnsupportedError('Unsupported HTTP method: $method');
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return {};
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else if (response.statusCode == 401 && path != '/api/v1/auth/refresh' && !isRetry) {
      // Automatic transparent token refresh and retry (limited to single retry)
      final refreshToken = await _storage.readRefreshToken();
      bool refreshSucceeded = false;
      if (refreshToken != null) {
        try {
          final refreshed = await post('/api/v1/auth/refresh', body: {'refresh_token': refreshToken});
          if (refreshed['success'] == true && refreshed['data']?['access_token'] != null) {
            await _storage.saveAuthToken(refreshed['data']['access_token']);
            refreshSucceeded = true;
          }
        } catch (_) {
          // Token refresh call failed
        }
      }

      if (refreshSucceeded) {
        // Replay original request outside refresh try-catch so transient errors don't wipe session
        return _sendRequest(method, path, body: body, isRetry: true);
      }

      // Terminal refresh failure: clear session and report expired auth
      await _storage.clearSession();
      final errorBody = response.body.isNotEmpty ? jsonDecode(response.body) : {};
      throw SanctuaryClientException(
        statusCode: response.statusCode,
        errorCode: errorBody['error_code'] ?? 'AUTH_EXPIRED',
        message: errorBody['message'] ?? 'Session expired',
      );
    } else {
      final errorBody = response.body.isNotEmpty ? jsonDecode(response.body) : {};
      throw SanctuaryClientException(
        statusCode: response.statusCode,
        errorCode: errorBody['error_code'] ?? 'UNKNOWN_ERROR',
        message: errorBody['message'] ?? 'Network request failed',
      );
    }
  }
}

class SanctuaryClientException implements Exception {
  final int statusCode;
  final String errorCode;
  final String message;

  SanctuaryClientException({
    required this.statusCode,
    required this.errorCode,
    required this.message,
  });

  @override
  String toString() => '[$errorCode ($statusCode)]: $message';
}

MD

1. Verification & Automated Test Suites
Frontend architecture and security invariants are verified using the following production test commands:
MD

Bash

# 1. Verify Android Keystore security and Window FLAG_SECURE policies

flutter test test/test_window_security_policy.dart

# 2. Verify static analysis and type safety across all Flutter files

dart analyze lib
