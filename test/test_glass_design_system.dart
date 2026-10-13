import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ur_heart/core/constants/app_typography.dart';
import 'package:ur_heart/core/theme/glass_performance_controller.dart';
import 'package:ur_heart/core/theme/glass_tokens.dart';
import 'package:ur_heart/core/theme/theme_controller.dart';
import 'package:ur_heart/core/theme/widgets/glass_navigation_shell_bars.dart';
import 'package:ur_heart/core/theme/widgets/glass_veil_widget.dart';
import 'package:ur_heart/core/theme/widgets/sanctuary_glass_container.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    GlassPerformanceController.enableLiveBackdropFilter = true;
    SharedPreferences.setMockInitialValues({'sanctuary_theme_dark_mode': true});
  });

  group('Glass Design System & Optical Physics Tests', () {
    testWidgets('Test 1: SanctuaryGlassContainer renders with backdrop filter & specular painter in Dark and Light themes', (WidgetTester tester) async {
      // 1. Dark Theme test
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: const Scaffold(
            body: SanctuaryGlassContainer(
              blurSigma: 12.0,
              child: Text('Dark Sanctuary Glass Card'),
            ),
          ),
        ),
      );

      expect(find.text('Dark Sanctuary Glass Card'), findsOneWidget);
      expect(find.byType(BackdropFilter), findsOneWidget);
      expect(find.byType(CustomPaint), findsWidgets);

      // Verify BackdropFilter has resolved 12.0 sigma
      final backdrop = tester.widget<BackdropFilter>(find.byType(BackdropFilter));
      expect(backdrop.filter, equals(ImageFilter.blur(sigmaX: 12.0, sigmaY: 12.0)));

      // 2. Light Theme test
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.light(),
          home: const Scaffold(
            body: SanctuaryGlassContainer(
              blurSigma: 18.0,
              child: Text('Light Sanctuary Milk-Glass Card'),
            ),
          ),
        ),
      );

      expect(find.text('Light Sanctuary Milk-Glass Card'), findsOneWidget);
      final backdropLight = tester.widget<BackdropFilter>(find.byType(BackdropFilter));
      expect(backdropLight.filter, equals(ImageFilter.blur(sigmaX: 18.0, sigmaY: 18.0)));
    });

    testWidgets('Test 2: GlassVeilWidget applies 35px blur veil when veiled, and reveals raw image when unveiled', (WidgetTester tester) async {
      bool consentRequested = false;

      // 1. Veiled State
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: GlassVeilWidget(
              isVeiled: true,
              seekerFirstName: 'Maya',
              onConsentRequested: () {
                consentRequested = true;
              },
              underlyingImage: const SizedBox(
                key: Key('raw_profile_photo'),
                width: 200,
                height: 200,
              ),
            ),
          ),
        ),
      );

      expect(find.byKey(const Key('raw_profile_photo')), findsOneWidget);
      expect(find.text('Veiled in Sacred Modesty'), findsOneWidget);
      expect(find.byIcon(Icons.remove_red_eye_outlined), findsOneWidget);
      expect(find.text('Request Reveal to Maya'), findsOneWidget);

      // Verify exact 35px Gaussian veil
      final backdrop = tester.widget<BackdropFilter>(find.byType(BackdropFilter));
      expect(backdrop.filter, equals(ImageFilter.blur(sigmaX: 35.0, sigmaY: 35.0)));

      // Trigger consent request
      await tester.tap(find.text('Request Reveal to Maya'));
      expect(consentRequested, isTrue);

      // 2. Unveiled State
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: const Scaffold(
            body: GlassVeilWidget(
              isVeiled: false,
              seekerFirstName: 'Maya',
              underlyingImage: SizedBox(
                key: Key('raw_profile_photo'),
                width: 200,
                height: 200,
              ),
            ),
          ),
        ),
      );

      expect(find.byKey(const Key('raw_profile_photo')), findsOneWidget);
      expect(find.text('Veiled in Sacred Modesty'), findsNothing);
      expect(find.byType(BackdropFilter), findsNothing);
    });

    test('Test 3: ThemeController toggles between Dark and Light state and persists preference', () async {
      SharedPreferences.setMockInitialValues({'sanctuary_theme_dark_mode': true});
      final controller = ThemeController();

      // Allow async initial load
      await Future<void>.delayed(const Duration(milliseconds: 10));
      expect(controller.state.isDark, isTrue);

      // Toggle to Light mode
      await controller.toggleTheme();
      expect(controller.state.isDark, isFalse);

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getBool('sanctuary_theme_dark_mode'), isFalse);

      // Toggle back to Dark mode
      await controller.toggleTheme();
      expect(controller.state.isDark, isTrue);
      expect(prefs.getBool('sanctuary_theme_dark_mode'), isTrue);
    });

    test('Test 4: GlassPerformanceController.resolveSigma() returns 0.0 when live blur is disabled', () {
      GlassPerformanceController.enableLiveBackdropFilter = true;
      expect(GlassPerformanceController.resolveSigma(12.0), equals(12.0));
      expect(GlassPerformanceController.resolveSigma(35.0), equals(35.0));

      // Simulate low-end device fallback
      GlassPerformanceController.initializePerformanceSettings(isLowEndDevice: true);
      expect(GlassPerformanceController.enableLiveBackdropFilter, isFalse);
      expect(GlassPerformanceController.resolveSigma(12.0), equals(0.0));
      expect(GlassPerformanceController.resolveSigma(35.0), equals(0.0));

      // Reset
      GlassPerformanceController.enableLiveBackdropFilter = true;
      expect(GlassPerformanceController.resolveSigma(24.0), equals(24.0));
    });

    testWidgets('Test 5: GlassAppBar and GlassBottomNavBar render with valid geometry', (WidgetTester tester) async {
      int navIndex = 0;

      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            appBar: const GlassAppBar(
              title: Text('Sanctuary Chamber'),
            ),
            bottomNavigationBar: GlassBottomNavBar(
              currentIndex: navIndex,
              onTap: (index) {
                navIndex = index;
              },
              items: const [
                BottomNavigationBarItem(icon: Icon(Icons.favorite), label: 'Resonance'),
                BottomNavigationBarItem(icon: Icon(Icons.chat), label: 'Dialogue'),
              ],
            ),
            body: const Center(child: Text('Main Content')),
          ),
        ),
      );

      expect(find.text('Sanctuary Chamber'), findsOneWidget);
      expect(find.text('Resonance'), findsOneWidget);
      expect(find.text('Dialogue'), findsOneWidget);

      await tester.tap(find.text('Dialogue'));
      expect(navIndex, equals(1));
    });

    test('Test 6: SanctuaryTypography and SanctuaryGlassTokens token contracts', () {
      final darkTokens = SanctuaryGlassTokens.dark();
      expect(darkTokens.isDark, isTrue);
      expect(darkTokens.backgroundCanvas, equals(const Color(0xFF0F1115)));
      expect(darkTokens.elevatedSurface, equals(const Color(0xFF181B20)));
      expect(SanctuaryGlassTokens.brandPine, equals(const Color(0xFF2D5A43)));
      expect(SanctuaryGlassTokens.brandSacredGold, equals(const Color(0xFFD4AF37)));

      final lightTokens = SanctuaryGlassTokens.light();
      expect(lightTokens.isDark, isFalse);
      expect(lightTokens.backgroundCanvas, equals(const Color(0xFFF9F6F0)));
      expect(lightTokens.elevatedSurface, equals(const Color(0xFFFFFFFF)));

      final h1Style = SanctuaryTypography.titleH1(Colors.white, isDark: true);
      expect(h1Style.fontSize, equals(32.0));
      expect(h1Style.fontWeight, equals(FontWeight.w700));
      expect(h1Style.fontFamily, equals(SanctuaryTypography.serifFont));
      expect(h1Style.shadows, equals(SanctuaryTypography.glassTextShadow));

      final bodyStyle = SanctuaryTypography.bodyStandard(Colors.black);
      expect(bodyStyle.fontSize, equals(14.5));
      expect(bodyStyle.fontFamily, equals(SanctuaryTypography.sansFont));
    });
  });
}
