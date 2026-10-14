import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:ur_heart/core/billing/sanctuary_billing_service.dart';
import 'package:ur_heart/features/growth/data/store_catalog_model.dart';
import 'package:ur_heart/features/growth/presentation/controllers/growth_hub_controller.dart';
import 'package:ur_heart/features/growth/presentation/screens/growth_hub_screen.dart';
import 'package:ur_heart/features/growth/presentation/widgets/streak_gauge_widget.dart';

class FakeBillingService implements SanctuaryBillingService {
  final Map<String, dynamic>? mockCatalog;
  final Map<String, dynamic>? mockBalances;

  FakeBillingService({this.mockCatalog, this.mockBalances});

  @override
  Future<Map<String, dynamic>> fetchStoreCatalog() async {
    return mockCatalog ??
        {
          'success': true,
          'data': {
            'currency': 'INR',
            'usd_enabled': false,
            'products': [
              {
                'id': 'direct_letter_single',
                'title': 'Direct Thought Letter',
                'description': 'Send an intentional direct letter.',
                'product_class': 'micro_perk',
                'inr_price': 29.0,
                'currency_symbol': '₹',
                'badge_label': 'Popular',
              },
              {
                'id': 'sacred_bridge_instant',
                'title': 'Instant Bridge Key',
                'description': 'Instant reveal of contact.',
                'product_class': 'micro_perk',
                'inr_price': 99.0,
                'currency_symbol': '₹',
                'badge_label': 'Instant',
              },
              {
                'id': 'pass_sovereign_weekly',
                'title': 'Sovereign Pass (7 Days)',
                'description': 'Unlimited Swipes, Ad-Free UI.',
                'product_class': 'pass',
                'inr_price': 299.0,
                'currency_symbol': '₹',
                'badge_label': '7 Days',
              },
            ],
          },
        };
  }

  @override
  Future<Map<String, dynamic>> fetchBalances() async {
    return mockBalances ??
        {
          'success': true,
          'data': {
            'reward_balance': 320,
            'streak_count': 9,
            'swipes_remaining': 28,
            'direct_letters_count': 4,
            'boost_points': 80,
            'subscription_tier': 'spark',
            'is_ad_free': false,
          },
        };
  }

  @override
  Future<Map<String, dynamic>> claimReward({
    required String transactionId,
    required String adType,
    required String network,
  }) async {
    return {'success': true, 'new_balance': 250};
  }
}

void main() {
  Widget buildTestApp({
    GrowthHubState? initialState,
    SanctuaryBillingService? billingService,
    void Function(StoreProduct)? onProductTap,
    VoidCallback? onAdHarvestTap,
  }) {
    final fakeService = billingService ?? FakeBillingService();

    return ProviderScope(
      overrides: [
        sanctuaryBillingServiceProvider.overrideWithValue(fakeService),
        if (initialState != null)
          growthHubControllerProvider.overrideWith((ref) {
            final c = GrowthHubController(fakeService);
            c.state = initialState;
            return c;
          }),
      ],
      child: MaterialApp(
        theme: ThemeData.dark(),
        home: GrowthHubScreen(
          onProductTap: onProductTap,
          onAdHarvestTap: onAdHarvestTap,
        ),
      ),
    );
  }

  testWidgets(
    'Test 1: GrowthHubScreen displays balance pill, streak gauge, and 4 rewarded ad triggers',
    (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      const state = GrowthHubState(
        rewardBalance: 320,
        streakCount: 9,
        restMultiplier: 1.5,
        isNightSlumberActive: true,
        directLettersCount: 4,
        swipesRemaining: 28,
        subscriptionTier: 'spark',
      );

      await tester.pumpWidget(buildTestApp(initialState: state));
      await tester.pumpAndSettle();

      // Top title and balance pill values
      expect(find.text('Growth Hub & Store'), findsOneWidget);
      expect(find.text('320'), findsOneWidget);
      expect(find.text('4'), findsOneWidget);
      expect(find.text('28'), findsOneWidget);

      // Streak Gauge & Slumber Card
      expect(find.byType(StreakGaugeWidget), findsOneWidget);
      expect(find.text('Night Slumber'), findsOneWidget);
      expect(find.text('1.5x'), findsOneWidget);

      // 4 Mindful Ad Reflection Triggers
      expect(find.text('Quick Reflection'), findsOneWidget);
      expect(find.text('Deep Resonance'), findsOneWidget);
      expect(find.text('Sacred Bridge Reveal'), findsOneWidget);
      expect(find.text('Harvest Boost'), findsOneWidget);
    },
  );

  testWidgets(
    'Test 2: Renders INR pricing (₹29, ₹99, ₹299) across store cards and anti-predatory notice',
    (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(buildTestApp());
      await tester.pumpAndSettle();

      // Verify micro-perk and pass INR prices are present
      expect(find.text('₹29'), findsOneWidget);
      expect(find.text('₹99'), findsOneWidget);
      expect(find.text('₹299'), findsOneWidget);

      // Verify anti-predatory non-recurring disclaimer
      expect(
        find.text('One-time mindful payment. Never auto-charged.'),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    'Test 3: Tapping a product card dispatches order initiation callback',
    (tester) async {
      tester.view.physicalSize = const Size(800, 1600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      StoreProduct? selectedProduct;

      await tester.pumpWidget(buildTestApp(
        onProductTap: (product) {
          selectedProduct = product;
        },
      ));
      await tester.pumpAndSettle();

      // Tap on the ₹29 purchase button for Direct Thought Letter
      final buyButton = find.text('₹29');
      expect(buyButton, findsOneWidget);

      await tester.tap(buyButton);
      await tester.pumpAndSettle();

      expect(selectedProduct, isNotNull);
      expect(selectedProduct!.id, 'direct_letter_single');
      expect(selectedProduct!.inrPrice, 29.0);
    },
  );
}
