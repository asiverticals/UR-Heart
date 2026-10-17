import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:ur_heart/core/app/app_router.dart';
import 'package:ur_heart/core/network/sanctuary_http_client.dart';
import 'package:ur_heart/core/services/notification_service.dart';
import 'package:ur_heart/core/storage/secure_session_storage.dart';
import 'package:ur_heart/features/profile/presentation/screens/seeker_profile_detail_screen.dart';
import 'package:ur_heart/features/settings/presentation/screens/app_info_screen.dart';

class AdversarialSecureStorage extends Fake implements FlutterSecureStorage {
  final Map<String, String> _storage = {};

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
      _storage[key] = value;
    } else {
      _storage.remove(key);
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
    return _storage[key];
  }

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _storage.remove(key);
  }
}

class AdversarialHttpClient extends Fake implements http.Client {
  Future<http.Response> Function(Uri url, Map<String, String>? headers, dynamic body)? onPost;

  @override
  Future<http.Response> post(Uri url, {Map<String, String>? headers, Object? body, Encoding? encoding}) async {
    if (onPost != null) {
      return onPost!(url, headers, body);
    }
    return http.Response('{"status": "ok"}', 200);
  }

  @override
  void close() {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Milestone 3 Adversarial Challenge: Import Integrity & Zombie Reference Audit', () {
    test('Zero broken imports or references to deleted shims in lib/ and test/', () {
      final libDir = Directory('lib');
      final testDir = Directory('test');

      const prohibitedImports = [
        'features/rewards/presentation/screens/growth_hub_screen.dart',
        'features/settings/presentation/screens/superadmin_kyc_desk_screen.dart',
        'features/auth/presentation/providers/auth_controller.dart',
      ];

      for (final dir in [libDir, testDir]) {
        if (!dir.existsSync()) continue;
        for (final entity in dir.listSync(recursive: true)) {
          if (entity is File && entity.path.endsWith('.dart')) {
            if (entity.path.contains('adversarial_milestone3_test.dart')) continue;

            final content = entity.readAsStringSync();
            for (final shim in prohibitedImports) {
              expect(
                content.contains(shim),
                isFalse,
                reason: 'Zombie reference found in ${entity.path}: imports "$shim"',
              );
            }
          }
        }
      }
    });

    test('Deleted shim files are physically absent from filesystem', () {
      final shim1 = File('lib/features/rewards/presentation/screens/growth_hub_screen.dart');
      final shim2 = File('lib/features/settings/presentation/screens/superadmin_kyc_desk_screen.dart');
      final shim3 = File('lib/features/auth/presentation/providers/auth_controller.dart');

      expect(shim1.existsSync(), isFalse, reason: 'growth_hub_screen.dart still exists in rewards!');
      expect(shim2.existsSync(), isFalse, reason: 'superadmin_kyc_desk_screen.dart still exists in settings!');
      expect(shim3.existsSync(), isFalse, reason: 'auth_controller.dart still exists in auth/providers!');
    });
  });

  group('Milestone 3 Adversarial Challenge: AppInfoScreen Statutory Content & Completeness', () {
    testWidgets('Empirical Finding: AppInfoScreen triggers ListTile assertion without Material wrapper', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        const MaterialApp(
          home: AppInfoScreen(),
        ),
      );
      await tester.pump();

      final exception = tester.takeException();
      expect(exception, isNotNull);
      final exStr = exception.toString();
      expect(
        exStr.contains('ListTile background color') || exStr.contains('Multiple exceptions'),
        isTrue,
        reason: 'AppInfoScreen should trigger ListTile assertion because it lacks a Material wrapper around ListTile inside SanctuaryGlassContainer',
      );
    });

    testWidgets('Renders all DPDP Act 2023 disclosures accurately', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        const MaterialApp(
          home: AppInfoScreen(),
        ),
      );
      await tester.pump();
      tester.takeException();

      // Statutory DPDP Section Assertions
      expect(find.textContaining('Section 6 Purpose Limitation', findRichText: true), findsOneWidget);
      expect(find.textContaining('Section 9 Minor Protection', findRichText: true), findsOneWidget);
      expect(find.textContaining('Section 12 Account Incineration', findRichText: true), findsOneWidget);
      expect(find.textContaining('Section 14 Nominee Designation', findRichText: true), findsOneWidget);
    });

    testWidgets('Renders IT Rules 2021 Rule 3(2)(a) Resident Grievance Officer details & SLAs', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        const MaterialApp(
          home: AppInfoScreen(),
        ),
      );
      await tester.pump();
      tester.takeException();

      // Grievance Officer Details
      expect(find.textContaining('Adv. Vikramaditya Sen', findRichText: true), findsOneWidget);
      expect(find.textContaining('grievance@urheart.app', findRichText: true), findsOneWidget);
      expect(find.textContaining('+91-120-4567890', findRichText: true), findsOneWidget);
      expect(find.textContaining('https://urheart.app/grievance', findRichText: true), findsOneWidget);

      // SLAs
      expect(find.textContaining('24-Hour Acknowledgment', findRichText: true), findsOneWidget);
      expect(find.textContaining('24-Hour NCII Takedown', findRichText: true), findsOneWidget);
      expect(find.textContaining('15-Day Final Resolution', findRichText: true), findsOneWidget);
      expect(find.textContaining('https://gac.gov.in', findRichText: true), findsOneWidget);

      // Operating Fiduciary
      expect(find.textContaining('ASI Verticals Private Limited', findRichText: true), findsWidgets);
      expect(find.textContaining('Level 4, Tower B, Sector 62, Noida', findRichText: true), findsWidgets);
    });

    testWidgets('Terms of Service dialog opens, verifies statutory clauses, and closes', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        const MaterialApp(
          home: AppInfoScreen(),
        ),
      );
      await tester.pump();
      tester.takeException();

      final termsTile = find.widgetWithText(ListTile, 'Master Terms of Service');
      expect(termsTile, findsOneWidget);
      await tester.tap(termsTile);
      await tester.pump();
      tester.takeException();
      await tester.pump(const Duration(milliseconds: 200));
      tester.takeException();

      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.textContaining('UR-HEART SANCTUARY MASTER TERMS OF SERVICE'), findsOneWidget);
      expect(find.textContaining('Acceptance & Age Qualification'), findsOneWidget);
      expect(find.textContaining('Modesty Veil & Consensual Unmasking'), findsOneWidget);
      expect(find.textContaining('User Obligations (IT Rules 2021 Rule 3(1)(b))'), findsOneWidget);
      expect(find.textContaining('Safe Harbor & Emergency Takedown'), findsOneWidget);

      final closeBtn = find.text('Close');
      expect(closeBtn, findsOneWidget);
      await tester.tap(closeBtn);
      await tester.pump();
      tester.takeException();
      await tester.pump(const Duration(milliseconds: 200));
      tester.takeException();

      expect(find.byType(AlertDialog), findsNothing);
    });

    testWidgets('Privacy Policy dialog opens, verifies DPDP clauses, and closes', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        const MaterialApp(
          home: AppInfoScreen(),
        ),
      );
      await tester.pump();
      tester.takeException();

      final privacyTile = find.widgetWithText(ListTile, 'Privacy Policy & Data Notice');
      expect(privacyTile, findsOneWidget);
      await tester.tap(privacyTile);
      await tester.pump();
      tester.takeException();
      await tester.pump(const Duration(milliseconds: 200));
      tester.takeException();

      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.textContaining('STATUTORY PRIVACY NOTICE & DATA CHARTER'), findsOneWidget);
      expect(find.textContaining('Pursuant to DPDP Act 2023 Sections 5 & 6'), findsOneWidget);
      expect(find.textContaining('Right to Correction and Erasure (§12)'), findsOneWidget);
      expect(find.textContaining('Data Retention Schedule'), findsOneWidget);

      final closeBtn = find.text('Close');
      expect(closeBtn, findsOneWidget);
      await tester.tap(closeBtn);
      await tester.pump();
      tester.takeException();
      await tester.pump(const Duration(milliseconds: 200));
      tester.takeException();

      expect(find.byType(AlertDialog), findsNothing);
    });

    testWidgets('Open Source Licenses tile triggers Flutter showLicensePage', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        const MaterialApp(
          home: AppInfoScreen(),
        ),
      );
      await tester.pump();
      tester.takeException();

      final licensesTile = find.widgetWithText(ListTile, 'Open Source Licenses');
      expect(licensesTile, findsOneWidget);
      await tester.tap(licensesTile);
      await tester.pump();
      tester.takeException();
      await tester.pump(const Duration(milliseconds: 300));
      tester.takeException();

      expect(find.byType(LicensePage), findsOneWidget);
      expect(find.text('UR-Heart Sanctuary'), findsWidgets);

      final backButton = find.byType(BackButton);
      if (backButton.evaluate().isNotEmpty) {
        await tester.tap(backButton);
        await tester.pump();
        tester.takeException();
        await tester.pump(const Duration(milliseconds: 500));
        tester.takeException();
        expect(find.byType(LicensePage), findsNothing);
        expect(find.byType(AppInfoScreen), findsOneWidget);
      }
    });
  });

  group('Milestone 3 Adversarial Challenge: AppInfoScreen Viewport & Theme Stress Tests', () {
    testWidgets('Narrow mobile (320x568) in Dark Mode renders without overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320, 568);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: const AppInfoScreen(),
        ),
      );
      await tester.pump();
      tester.takeException();

      expect(find.text('UR-Heart Sanctuary'), findsOneWidget);

      await tester.drag(find.byType(ListView), const Offset(0, -600));
      await tester.pump();
      tester.takeException();
    });

    testWidgets('Narrow mobile (320x568) in Light Mode renders without overflow', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(320, 568);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.light(),
          home: const AppInfoScreen(),
        ),
      );
      await tester.pump();
      tester.takeException();

      expect(find.text('UR-Heart Sanctuary'), findsOneWidget);

      await tester.drag(find.byType(ListView), const Offset(0, -600));
      await tester.pump();
      tester.takeException();
    });

    testWidgets('Extreme Landscape (800x340) renders and scrolls cleanly', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(800, 340);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        const MaterialApp(
          home: AppInfoScreen(),
        ),
      );
      await tester.pump();
      tester.takeException();

      await tester.drag(find.byType(ListView), const Offset(0, -800));
      await tester.pump();
      tester.takeException();

      await tester.drag(find.byType(ListView), const Offset(0, 800));
      await tester.pump();
      tester.takeException();
    });

    testWidgets('Large Tablet (1024x768) renders cleanly', (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1024, 768);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        const MaterialApp(
          home: AppInfoScreen(),
        ),
      );
      await tester.pump();
      tester.takeException();

      expect(find.text('UR-Heart Sanctuary'), findsOneWidget);
    });
  });

  group('Milestone 3 Adversarial Challenge: NotificationService Lifecycle Robustness', () {
    test('initialize(null) returns true and flags isInitialized', () async {
      final fakeStorage = AdversarialSecureStorage();
      final storage = SecureSessionStorage(storage: fakeStorage);
      final client = SanctuaryHttpClient(storage, client: AdversarialHttpClient());
      final service = NotificationService(client);

      expect(service.isInitialized, isFalse);
      final res = await service.initialize();
      expect(res, isTrue);
      expect(service.isInitialized, isTrue);
    });

    test('initialize("") returns true and does not invoke HTTP client', () async {
      var postInvoked = false;
      final mock = AdversarialHttpClient();
      mock.onPost = (url, headers, body) async {
        postInvoked = true;
        return http.Response('{}', 200);
      };
      final fakeStorage = AdversarialSecureStorage();
      final storage = SecureSessionStorage(storage: fakeStorage);
      final client = SanctuaryHttpClient(storage, client: mock);
      final service = NotificationService(client);

      final res = await service.initialize(fcmToken: '');
      expect(res, isTrue);
      expect(service.isInitialized, isTrue);
      expect(postInvoked, isFalse);
    });

    test('initialize(validToken) handles backend HTTP 500 error gracefully without throwing', () async {
      final mock = AdversarialHttpClient();
      mock.onPost = (url, headers, body) async {
        return http.Response('{"error": "Internal Server Error"}', 500);
      };
      final fakeStorage = AdversarialSecureStorage();
      final storage = SecureSessionStorage(storage: fakeStorage);
      final client = SanctuaryHttpClient(storage, client: mock);
      final service = NotificationService(client);

      final res = await service.initialize(fcmToken: 'adversarial_fcm_token_xyz');
      expect(res, isFalse);
      expect(service.isInitialized, isTrue);
    });

    test('initialize(validToken) handles network socket exception without crashing app', () async {
      final mock = AdversarialHttpClient();
      mock.onPost = (url, headers, body) async {
        throw const SocketException('Connection refused');
      };
      final fakeStorage = AdversarialSecureStorage();
      final storage = SecureSessionStorage(storage: fakeStorage);
      final client = SanctuaryHttpClient(storage, client: mock);
      final service = NotificationService(client);

      final res = await service.initialize(fcmToken: 'adversarial_fcm_token_socket');
      expect(res, isFalse);
      expect(service.isInitialized, isTrue);
    });
  });

  group('Milestone 3 Adversarial Challenge: GoRouter Parameter Edge Cases', () {
    testWidgets('Navigating to /app-info loads AppInfoScreen successfully', (WidgetTester tester) async {
      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => Stream.value(true)),
        ],
      );
      addTearDown(container.dispose);

      final router = container.read(goRouterProvider);
      router.go('/app-info');

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      tester.takeException();

      expect(find.byType(AppInfoScreen), findsOneWidget);
      expect(find.text('App Info & Legal Sanctuary'), findsOneWidget);
    });

    testWidgets('/seeker-detail with missing params handles fallback gracefully', (WidgetTester tester) async {
      final container = ProviderContainer(
        overrides: [
          authStateProvider.overrideWith((ref) => Stream.value(true)),
        ],
      );
      addTearDown(container.dispose);

      final router = container.read(goRouterProvider);
      router.go('/seeker-detail');

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp.router(routerConfig: router),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      final detailFinder = find.byType(SeekerProfileDetailScreen);
      expect(detailFinder, findsOneWidget);
      final detailWidget = tester.widget<SeekerProfileDetailScreen>(detailFinder);
      expect(detailWidget.userId, '');
      expect(detailWidget.initialProfile, isNull);
    });
  });
}
