import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/services/slumber_service.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/growth/presentation/widgets/morning_harvest_dialog.dart';
import 'package:ur_heart/features/growth/presentation/widgets/streak_gauge_widget.dart';

class TestSecureStorage extends Fake implements FlutterSecureStorage {
  final Map<String, String> _data = {};

  @override
  Future<void> write({
    required String key,
    required String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value != null) {
      _data[key] = value;
    } else {
      _data.remove(key);
    }
  }

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    return _data[key];
  }
}

class FakeHttpClient extends Fake implements http.Client {
  Future<http.Response> Function(Uri url, Map<String, String>? headers, Object? body)? onPost;

  @override
  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Encoding? encoding,
  }) async {
    if (onPost != null) return onPost!(url, headers, body);
    return http.Response('{}', 200);
  }

  @override
  void close() {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Phase 5 — Chunk 5.3: Mindful Streak & Slumber Harvest Tests', () {
    testWidgets('Test 1: StreakGaugeWidget renders arc and streak day count accurately', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: StreakGaugeWidget(
                streakCount: 7,
                remainingSeconds: 43200, // 12 hours remaining
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('7 Days'), findsOneWidget);
      expect(find.text('12h Left'), findsOneWidget);
      expect(find.byIcon(Icons.local_fire_department_rounded), findsOneWidget);
    });

    testWidgets('Test 2: MorningHarvestDialog accurately displays awarded multiplier and dispatches claim mutation', (tester) async {
      final fakeStorage = TestSecureStorage();
      await fakeStorage.write(key: 'auth_token', value: 'fake_jwt_token');
      final sessionStorage = SecureSessionStorage(storage: fakeStorage);
      final fakeHttp = FakeHttpClient();

      bool claimCalled = false;
      double? claimedSleepHours;

      fakeHttp.onPost = (url, headers, body) async {
        if (url.path == '/api/v1/streak/claim-morning-harvest') {
          claimCalled = true;
          final decoded = jsonDecode(body.toString()) as Map<String, dynamic>;
          claimedSleepHours = (decoded['sleep_duration_hours'] as num).toDouble();
          return http.Response(
            jsonEncode({
              'data': {
                'sleep_duration_hours': claimedSleepHours,
                'multiplier': 2.0,
                'swipes_awarded': 20,
                'boost_points_awarded': 25,
                'direct_letters_awarded': 2,
                'new_streak_count': 6,
                'new_boost_points': 105,
                'new_swipes_remaining': 30,
                'new_direct_letters_count': 3,
                'message': 'Restorative deep slumber blessed your sanctuary with maximum vital energy.',
              }
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      };

      final client = SanctuaryHttpClient(sessionStorage, client: fakeHttp);
      bool harvestSuccessInvoked = false;

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            sanctuaryHttpClientProvider.overrideWithValue(client),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: MorningHarvestDialog(
                sleepHours: 8.5,
                onHarvestSuccess: () {
                  harvestSuccessInvoked = true;
                },
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify UI displays Deep Slumber 2.0x rewards preview
      expect(find.text('The Dawn Harvest'), findsOneWidget);
      expect(find.text('Conscious rest brings intentional energy.'), findsOneWidget);
      expect(find.text('8.5 Hours Restful Slumber • 2.0x Multiplier'), findsOneWidget);
      expect(find.text('+20 Swipes'), findsOneWidget);
      expect(find.text('+25 Points'), findsOneWidget);
      expect(find.text('+2 Direct Letters'), findsOneWidget);

      // Tap CTA to harvest
      await tester.tap(find.text('Harvest Intentional Swipes'));
      await tester.pumpAndSettle();

      expect(claimCalled, isTrue);
      expect(claimedSleepHours, equals(8.5));
      expect(harvestSuccessInvoked, isTrue);
    });

    test('Test 3: SlumberService computes elapsed rest and enforces clamping with baseline fallback', () async {
      final service = SlumberService();

      // No markers recorded -> defaults to baseline 7.0 hours
      final defaultHours = await service.resolveLastNightSleepHours();
      expect(defaultHours, equals(7.0));

      // 8.0 hours recorded
      final start = DateTime(2026, 10, 13, 22, 0, 0);
      final end = DateTime(2026, 10, 14, 6, 0, 0);
      await service.recordSlumberStart(start);
      await service.recordSlumberEnd(end);

      final recordedHours = await service.resolveLastNightSleepHours();
      expect(recordedHours, equals(8.0));

      // Over-sleep clamped to 12.0 hours
      final longEnd = DateTime(2026, 10, 14, 15, 0, 0); // 17 hours
      await service.recordSlumberEnd(longEnd);
      final clampedHours = await service.resolveLastNightSleepHours();
      expect(clampedHours, equals(12.0));
    });

    test('Test 4: SlumberService validates morning harvest window and prevents same-day duplicate claim', () async {
      final service = SlumberService();

      // At 03:00 (too early) -> False
      final nightTime = DateTime(2026, 10, 14, 3, 0, 0);
      expect(await service.isMorningHarvestAvailable(now: nightTime), isFalse);

      // At 14:00 (afternoon: too late) -> False
      final afternoonTime = DateTime(2026, 10, 14, 14, 0, 0);
      expect(await service.isMorningHarvestAvailable(now: afternoonTime), isFalse);

      // At 08:30 (morning window) -> True
      final morningTime = DateTime(2026, 10, 14, 8, 30, 0);
      expect(await service.isMorningHarvestAvailable(now: morningTime), isTrue);

      // Claim harvest
      await service.markHarvestClaimed(now: morningTime);

      // Subsequent check on same date at 10:00 -> False (already claimed)
      final laterMorning = DateTime(2026, 10, 14, 10, 0, 0);
      expect(await service.isMorningHarvestAvailable(now: laterMorning), isFalse);

      // Next morning at 08:00 -> True again
      final nextDay = DateTime(2026, 10, 15, 8, 0, 0);
      expect(await service.isMorningHarvestAvailable(now: nextDay), isTrue);
    });

    testWidgets('Test 5: StreakGaugeWidget displays minute-accurate countdown during the final hour', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: StreakGaugeWidget(
                streakCount: 3,
                remainingSeconds: 1800, // 30 minutes remaining
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('3 Days'), findsOneWidget);
      expect(find.text('30m Left'), findsOneWidget);
      expect(find.text('0h Left'), findsNothing);

      // Sub-minute countdown
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: StreakGaugeWidget(
                streakCount: 3,
                remainingSeconds: 45, // <1 minute
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('<1m Left'), findsOneWidget);
    });

    test('Test 6: SlumberService scopes harvest claims by account ID', () async {
      final service = SlumberService();
      final morningTime = DateTime(2026, 10, 14, 9, 0, 0);

      // User A claims harvest
      await service.markHarvestClaimed(userId: 'seeker_alpha', now: morningTime);

      // User A is blocked from duplicate claim
      expect(await service.isMorningHarvestAvailable(userId: 'seeker_alpha', now: morningTime), isFalse);

      // User B on same device is NOT blocked
      expect(await service.isMorningHarvestAvailable(userId: 'seeker_beta', now: morningTime), isTrue);

      // User B claims harvest
      await service.markHarvestClaimed(userId: 'seeker_beta', now: morningTime);
      expect(await service.isMorningHarvestAvailable(userId: 'seeker_beta', now: morningTime), isFalse);
    });

    test('Test 7: startSlumberTracking starts fresh sleep period and clears stale end marker', () async {
      final service = SlumberService();

      // Night 1
      final night1Start = DateTime(2026, 10, 13, 22, 0, 0);
      final night1End = DateTime(2026, 10, 14, 6, 0, 0);
      await service.recordSlumberStart(night1Start);
      await service.recordSlumberEnd(night1End);
      expect(await service.resolveLastNightSleepHours(), equals(8.0));

      // Night 2 starts: startSlumberTracking clears old end marker
      final night2Start = DateTime(2026, 10, 14, 23, 0, 0);
      await service.startSlumberTracking(night2Start);

      // Prior to Night 2 wake, resolveLastNightSleepHours returns baseline fallback (not night1End)
      expect(await service.resolveLastNightSleepHours(), equals(7.0));

      // Night 2 wake event
      final night2End = DateTime(2026, 10, 15, 5, 0, 0); // 6 hours
      await service.recordSlumberEnd(night2End);
      expect(await service.resolveLastNightSleepHours(), equals(6.0));
    });
  });
}
